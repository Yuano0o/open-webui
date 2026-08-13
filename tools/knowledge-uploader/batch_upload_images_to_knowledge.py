#!/usr/bin/env python3
"""Idempotently upload scientific images into an Open WebUI knowledge base."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


SUPPORTED_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}
ASSET_NUMBER_PATTERN = re.compile(
    r'(?:figure|fig|table)[_\s.-]*(?P<number>\d+[A-Za-z]?)', re.IGNORECASE
)


class UploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class Asset:
    path: Path
    relative_path: str
    sha256: str
    metadata: dict[str, Any]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _paper_metadata(source_root: Path, doi_slug: str) -> dict[str, Any]:
    knowledge_area = source_root.parent.parent
    metadata_path = knowledge_area / 'papers' / doi_slug / 'metadata.json'
    if not metadata_path.is_file():
        return {}
    try:
        value = json.loads(metadata_path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_asset(path: Path, source_root: Path) -> Asset:
    relative = path.relative_to(source_root)
    paper_folder = relative.parts[0]
    paper_id, separator, doi_slug = paper_folder.partition('__')
    doi = doi_slug.replace('_', '/', 1) if separator else ''

    parts = {part.lower() for part in relative.parts}
    asset_type = 'table' if 'tables' in parts else 'figure'
    number_match = ASSET_NUMBER_PATTERN.search(path.stem)
    asset_number = number_match.group('number') if number_match else ''

    caption_path = path.with_name(f'{path.stem}_caption.md')
    if not caption_path.is_file() and asset_type == 'table':
        caption_path = path.with_suffix('.md')
    caption = ''
    if caption_path.is_file():
        caption = caption_path.read_text(encoding='utf-8', errors='replace').strip()

    paper_metadata = _paper_metadata(source_root, doi_slug)
    digest = sha256_file(path)
    metadata: dict[str, Any] = {
        'paper_id': paper_id.upper() if separator else '',
        'doi': doi,
        'asset_type': asset_type,
        'asset_no': asset_number,
        'paper_title': str(paper_metadata.get('title') or paper_metadata.get('publisher_title') or ''),
        'caption': caption,
        'source_relative_path': relative.as_posix(),
        'file_hash': digest,
    }
    if asset_type == 'figure' and asset_number:
        metadata['figure_no'] = asset_number
    return Asset(path=path, relative_path=relative.as_posix(), sha256=digest, metadata=metadata)


def discover_assets(source_root: Path, only: str = 'all') -> list[Asset]:
    candidates = sorted(
        path
        for path in source_root.rglob('*')
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    assets = [build_asset(path, source_root) for path in candidates]
    if only != 'all':
        assets = [asset for asset in assets if asset.metadata['asset_type'] == only.removesuffix('s')]
    return assets


class OpenWebUIClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 600):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        request_headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            **(headers or {}),
        }
        request = Request(
            f'{self.base_url}{path}',
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except HTTPError as exc:
            payload = exc.read().decode('utf-8', errors='replace')
            try:
                detail = json.loads(payload).get('detail', payload)
            except json.JSONDecodeError:
                detail = payload
            raise UploadError(f'HTTP {exc.code}: {detail}') from exc
        except URLError as exc:
            raise UploadError(f'Cannot reach Open WebUI: {exc.reason}') from exc
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise UploadError('Open WebUI returned invalid JSON') from exc

    def resolve_knowledge(self, name_or_id: str) -> dict[str, Any]:
        page = 1
        matches: list[dict[str, Any]] = []
        while True:
            response = self._request_json('GET', f'/knowledge/?page={page}')
            items = response.get('items', []) if isinstance(response, dict) else []
            matches.extend(
                item
                for item in items
                if item.get('id') == name_or_id or item.get('name') == name_or_id
            )
            if not items or page * len(items) >= int(response.get('total', 0)):
                break
            page += 1
        unique = {item['id']: item for item in matches if item.get('id')}
        if len(unique) != 1:
            raise UploadError(
                f'Expected exactly one knowledge base named/id {name_or_id!r}; found {len(unique)}'
            )
        return next(iter(unique.values()))

    def existing_keys(self, knowledge_id: str) -> tuple[set[str], set[str]]:
        hashes: set[str] = set()
        relative_paths: set[str] = set()
        page = 1
        while True:
            response = self._request_json(
                'GET', f'/knowledge/{quote(knowledge_id)}/files?page={page}'
            )
            items = response.get('items', []) if isinstance(response, dict) else []
            for item in items:
                meta = item.get('meta') or {}
                if meta.get('file_hash'):
                    hashes.add(str(meta['file_hash']))
                source_path = (meta.get('data') or {}).get('source_relative_path')
                if source_path:
                    relative_paths.add(str(source_path))
            if not items or page * len(items) >= int(response.get('total', 0)):
                break
            page += 1
        return hashes, relative_paths

    def upload(self, asset: Asset, knowledge_id: str) -> dict[str, Any]:
        metadata = {**asset.metadata, 'knowledge_id': knowledge_id}
        boundary = f'----OpenWebUIVision{uuid.uuid4().hex}'
        mime_type = mimetypes.guess_type(asset.path.name)[0] or 'application/octet-stream'
        filename = asset.path.name.replace('"', '')
        body = b''.join(
            [
                f'--{boundary}\r\n'.encode(),
                (
                    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                    f'Content-Type: {mime_type}\r\n\r\n'
                ).encode('utf-8'),
                asset.path.read_bytes(),
                b'\r\n',
                f'--{boundary}\r\n'.encode(),
                b'Content-Disposition: form-data; name="metadata"\r\n',
                b'Content-Type: application/json; charset=utf-8\r\n\r\n',
                json.dumps(metadata, ensure_ascii=False).encode('utf-8'),
                b'\r\n',
                f'--{boundary}--\r\n'.encode(),
            ]
        )
        response = self._request_json(
            'POST',
            '/files/?process=true&process_in_background=false',
            body=body,
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': str(len(body)),
            },
        )
        file_id = response.get('id') if isinstance(response, dict) else None
        if not file_id:
            raise UploadError('Open WebUI upload response did not contain a file id')

        # The synchronous upload endpoint can return the original file model even when
        # processing updated its database status to failed. Re-read before reporting success.
        file_record = self._request_json('GET', f'/files/{quote(file_id)}')
        file_data = (file_record.get('data') or {}) if isinstance(file_record, dict) else {}
        status = file_data.get('status')
        if status != 'completed':
            detail = file_data.get('error') or f'unexpected processing status {status!r}'
            try:
                self._request_json('DELETE', f'/files/{quote(file_id)}')
            except Exception as cleanup_error:
                detail = f'{detail}; failed-file cleanup also failed: {cleanup_error}'
            raise UploadError(str(detail))
        return file_record


def append_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + '\n')


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--knowledge', required=True, help='Exact knowledge name or UUID')
    parser.add_argument(
        '--base-url',
        default=os.getenv('OPEN_WEBUI_API_BASE_URL', 'http://127.0.0.1:8080/api/v1'),
    )
    parser.add_argument('--only', choices=('all', 'figures', 'tables'), default='all')
    parser.add_argument('--limit', type=int, default=0, help='For a small test run; 0 means all')
    parser.add_argument('--retries', type=int, default=3, help='Attempts per image')
    parser.add_argument('--retry-delay', type=float, default=10, help='Base retry delay in seconds')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--log', type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_root = args.source.expanduser().resolve()
    if not source_root.is_dir():
        print(f'错误：图片目录不存在：{source_root}', file=sys.stderr)
        return 2
    assets = discover_assets(source_root, args.only)
    if args.limit > 0:
        assets = assets[: args.limit]
    print(f'发现 {len(assets)} 张待检查图片：{source_root}')
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
    log_path = args.log or source_root.parent / 'batch_image_upload.jsonl'

    uploaded = skipped = failed = 0
    for index, asset in enumerate(assets, start=1):
        prefix = f'[{index}/{len(assets)}] {asset.relative_path}'
        if asset.sha256 in existing_hashes or asset.relative_path in existing_paths:
            skipped += 1
            print(f'{prefix}：已存在，跳过')
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
                    print(f'{prefix}：处理失败，{delay:g} 秒后重试（{attempt}/{args.retries}）')
                    time.sleep(delay)

            file_id = response.get('id') if isinstance(response, dict) else None
            uploaded += 1
            existing_hashes.add(asset.sha256)
            existing_paths.add(asset.relative_path)
            append_log(
                log_path,
                {
                    'status': 'uploaded',
                    'source': asset.relative_path,
                    'sha256': asset.sha256,
                    'file_id': file_id,
                    'knowledge_id': knowledge_id,
                },
            )
            print(f'{prefix}：上传并入库完成（file_id={file_id}）')
        except Exception as exc:
            failed += 1
            append_log(
                log_path,
                {
                    'status': 'failed',
                    'source': asset.relative_path,
                    'sha256': asset.sha256,
                    'error': str(exc),
                    'knowledge_id': knowledge_id,
                },
            )
            print(f'{prefix}：失败：{exc}', file=sys.stderr)

    print(
        f'完成：知识库={knowledge["name"]}，新增={uploaded}，跳过={skipped}，失败={failed}'
    )
    print(f'记录：{log_path}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
