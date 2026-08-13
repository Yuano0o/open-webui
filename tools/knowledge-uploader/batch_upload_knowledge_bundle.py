#!/usr/bin/env python3
"""Upload a prepared Open WebUI knowledge bundle, excluding image files and logs."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from batch_upload_images_to_knowledge import (
    Asset,
    OpenWebUIClient,
    UploadError,
    append_log,
    sha256_file,
)


# Upload the searchable bundle representation. XML/HTML duplicate adjacent Markdown/CSV
# tables, while PDF/XLSX currently route to an unavailable external Docling service on
# Open WebUI Desktop. Original figures are handled by the separate vision importer.
SUPPORTED_SUFFIXES = {'.md', '.csv'}
PAPER_ID_PATTERN = re.compile(r'\[(?P<paper_id>[A-Z]{2}\d{2})\]')
DOI_FOLDER_PATTERN = re.compile(r'^[A-Z]{2}\d{2}__(?P<doi>.+)$')
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(?P<body>.*?)\n---\s*$', re.DOTALL | re.MULTILINE)


def _frontmatter(path: Path) -> dict[str, str]:
    if path.suffix.lower() != '.md':
        return {}
    text = path.read_text(encoding='utf-8', errors='replace')
    match = FRONTMATTER_PATTERN.search(text)
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group('body').splitlines():
        key, separator, value = line.partition(':')
        if separator and re.fullmatch(r'[A-Za-z0-9_-]+', key.strip()):
            values[key.strip()] = value.strip().strip('"\'')
    return values


def build_asset(path: Path, source_root: Path) -> Asset:
    relative = path.relative_to(source_root)
    frontmatter = _frontmatter(path)
    filename_id = PAPER_ID_PATTERN.search(path.name)
    paper_id = str(frontmatter.get('paper_id') or (filename_id.group('paper_id') if filename_id else ''))
    doi = str(frontmatter.get('doi') or '')

    if relative.parts and relative.parts[0] == '_assets' and len(relative.parts) > 1:
        folder_match = DOI_FOLDER_PATTERN.match(relative.parts[1])
        if folder_match:
            paper_id = paper_id or relative.parts[1].split('__', 1)[0]
            doi = doi or folder_match.group('doi').replace('_', '/', 1)

    if relative.parts and relative.parts[0] == '_visual_sources':
        stem = path.stem.split('__VISUAL_SOURCE__', 1)
        if len(stem) == 2:
            doi = doi or stem[1].replace('_', '/', 1)

    category = 'article'
    if path.name.startswith('[CATALOG]'):
        category = 'catalog'
    elif '_visual_sources' in relative.parts:
        category = 'visual_source'
    elif 'supplementary' in relative.parts:
        category = 'supplementary'
    elif 'tables' in relative.parts:
        category = 'table'
    elif 'figures' in relative.parts:
        category = 'figure_caption'

    digest = sha256_file(path)
    metadata = {
        'paper_id': paper_id,
        'doi': doi,
        'knowledge_role': frontmatter.get('knowledge_role', ''),
        'document_type': category,
        'source_relative_path': relative.as_posix(),
        'file_hash': digest,
    }
    return Asset(path=path, relative_path=relative.as_posix(), sha256=digest, metadata=metadata)


def discover_assets(source_root: Path) -> list[Asset]:
    return [
        build_asset(path, source_root)
        for path in sorted(source_root.rglob('*'))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--knowledge', required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:8080/api/v1')
    parser.add_argument('--retries', type=int, default=3)
    parser.add_argument('--retry-delay', type=float, default=10)
    parser.add_argument('--delay', type=float, default=0.5, help='Pause between successful files')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--log', type=Path)
    return parser.parse_args()


def main() -> int:
    import os

    args = parse_args()
    source_root = args.source.expanduser().resolve()
    if not source_root.is_dir():
        print(f'错误：知识库 bundle 不存在：{source_root}', file=sys.stderr)
        return 2
    assets = discover_assets(source_root)
    print(f'发现 {len(assets)} 个非图片知识文件：{source_root}', flush=True)
    if args.dry_run:
        for asset in assets:
            print(f'[DRY-RUN] {asset.relative_path} {asset.metadata}')
        return 0

    api_key = os.getenv('OPEN_WEBUI_API_KEY', '')
    if not api_key:
        print('错误：未设置 OPEN_WEBUI_API_KEY。', file=sys.stderr)
        return 2

    client = OpenWebUIClient(args.base_url, api_key)
    knowledge = client.resolve_knowledge(args.knowledge)
    knowledge_id = knowledge['id']
    existing_hashes, existing_paths = client.existing_keys(knowledge_id)
    log_path = args.log or source_root / 'batch_bundle_upload.jsonl'
    uploaded = skipped = failed = 0

    for index, asset in enumerate(assets, start=1):
        prefix = f'[{index}/{len(assets)}] {asset.relative_path}'
        if asset.sha256 in existing_hashes or asset.relative_path in existing_paths:
            skipped += 1
            print(f'{prefix}：已存在，跳过', flush=True)
            continue

        try:
            response = None
            for attempt in range(1, max(args.retries, 1) + 1):
                try:
                    response = client.upload(asset, knowledge_id)
                    break
                except Exception:
                    if attempt >= max(args.retries, 1):
                        raise
                    delay = args.retry_delay * attempt
                    print(f'{prefix}：处理失败，{delay:g} 秒后重试（{attempt}/{args.retries}）', flush=True)
                    time.sleep(delay)

            file_id = response.get('id') if isinstance(response, dict) else None
            uploaded += 1
            existing_hashes.add(asset.sha256)
            existing_paths.add(asset.relative_path)
            append_log(log_path, {
                'status': 'uploaded',
                'source': asset.relative_path,
                'sha256': asset.sha256,
                'file_id': file_id,
                'knowledge_id': knowledge_id,
            })
            print(f'{prefix}：上传并入库完成（file_id={file_id}）', flush=True)
            if args.delay > 0:
                time.sleep(args.delay)
        except Exception as exc:
            failed += 1
            append_log(log_path, {
                'status': 'failed',
                'source': asset.relative_path,
                'sha256': asset.sha256,
                'error': str(exc),
                'knowledge_id': knowledge_id,
            })
            print(f'{prefix}：失败：{exc}', file=sys.stderr, flush=True)

    print(f'完成：知识库={knowledge["name"]}，新增={uploaded}，跳过={skipped}，失败={failed}', flush=True)
    print(f'记录：{log_path}', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
