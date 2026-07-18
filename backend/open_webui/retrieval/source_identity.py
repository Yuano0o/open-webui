from __future__ import annotations

from typing import Any


def build_file_source_metadata(
    file_meta: dict | None,
    *,
    file_id: str,
    filename: str,
) -> dict:
    """Preserve file metadata while keeping canonical source fields authoritative."""
    metadata = file_meta if isinstance(file_meta, dict) else {}
    return {
        **metadata,
        'file_id': file_id,
        'name': filename,
        'source': filename,
    }


def add_source_identity_to_chunks(docs: list[Any]) -> list[Any]:
    """Embed stable source identifiers into every chunk's searchable text."""
    for doc in docs:
        metadata = doc.metadata or {}
        source_name = metadata.get('name') or metadata.get('title') or metadata.get('source')
        identity_lines = ([f'Document: {source_name}'] if source_name else []) + [
            f'{label}: {metadata[key]}'
            for key, label in (
                ('paper_id', 'paper_id'),
                ('review_id', 'review_id'),
                ('figure_no', 'figure_no'),
                ('asset_no', 'asset_no'),
                ('doi', 'DOI'),
            )
            if metadata.get(key) not in (None, '')
        ]
        if not identity_lines:
            continue

        leading_lines = set(doc.page_content.splitlines()[: len(identity_lines) + 1])
        missing_lines = [line for line in identity_lines if line not in leading_lines]
        if missing_lines:
            identity_prefix = '\n'.join(missing_lines)
            doc.page_content = f'{identity_prefix}\n{doc.page_content}'
    return docs
