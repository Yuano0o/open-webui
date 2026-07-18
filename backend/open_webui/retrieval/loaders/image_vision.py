from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import quote

import httpx
from langchain_core.documents import Document

SUPPORTED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
IMAGE_VISION_LOADER_URL = os.getenv('IMAGE_VISION_LOADER_URL', 'http://127.0.0.1:8765').rstrip('/')
IMAGE_VISION_LOADER_API_KEY = os.getenv('IMAGE_VISION_LOADER_API_KEY', '')
IMAGE_VISION_LOADER_TIMEOUT = float(os.getenv('IMAGE_VISION_LOADER_TIMEOUT', '180'))
IMAGE_VISION_MAX_BYTES = int(os.getenv('IMAGE_VISION_MAX_BYTES', str(10 * 1024 * 1024)))


class ImageVisionLoaderError(RuntimeError):
    pass


def _validate_signature(data: bytes, media_type: str) -> None:
    valid = {
        'image/jpeg': data.startswith(b'\xff\xd8\xff'),
        'image/png': data.startswith(b'\x89PNG\r\n\x1a\n'),
        'image/webp': len(data) >= 12 and data.startswith(b'RIFF') and data[8:12] == b'WEBP',
    }
    if not valid.get(media_type, False):
        raise ImageVisionLoaderError(f'File signature does not match {media_type}')


def _build_request_headers(*, filename: str, media_type: str, metadata: dict) -> dict[str, str]:
    headers = {
        'Content-Type': media_type,
        'X-Filename': quote(filename),
    }
    if IMAGE_VISION_LOADER_API_KEY:
        headers['Authorization'] = f'Bearer {IMAGE_VISION_LOADER_API_KEY}'
    for key, header in (
        ('paper_id', 'X-Paper-ID'),
        ('figure_no', 'X-Figure-No'),
        ('doi', 'X-DOI'),
    ):
        value = metadata.get(key)
        if value:
            headers[header] = str(value)
    return headers


async def load_image_with_vision(
    *,
    file_path: str,
    filename: str,
    media_type: str,
    metadata: dict | None = None,
) -> Document:
    if media_type not in SUPPORTED_IMAGE_TYPES:
        raise ImageVisionLoaderError(f'Unsupported image type: {media_type}')
    if not IMAGE_VISION_LOADER_URL:
        raise ImageVisionLoaderError('IMAGE_VISION_LOADER_URL is not configured')

    data = await asyncio.to_thread(Path(file_path).read_bytes)
    if not data:
        raise ImageVisionLoaderError('Image is empty')
    if len(data) > IMAGE_VISION_MAX_BYTES:
        raise ImageVisionLoaderError(f'Image exceeds {IMAGE_VISION_MAX_BYTES} bytes')
    _validate_signature(data, media_type)

    headers = _build_request_headers(
        filename=filename,
        media_type=media_type,
        metadata=metadata or {},
    )

    async with httpx.AsyncClient(timeout=IMAGE_VISION_LOADER_TIMEOUT) as client:
        response = await client.put(f'{IMAGE_VISION_LOADER_URL}/process', content=data, headers=headers)
    if response.is_error:
        raise ImageVisionLoaderError(
            f'Image vision loader failed with HTTP {response.status_code}: {response.text[:500]}'
        )
    payload = response.json()
    page_content = payload.get('page_content')
    result_metadata = payload.get('metadata') or {}
    if not isinstance(page_content, str) or not page_content.strip():
        raise ImageVisionLoaderError('Image vision loader returned empty page_content')
    if not isinstance(result_metadata, dict):
        raise ImageVisionLoaderError('Image vision loader returned invalid metadata')
    return Document(page_content=page_content, metadata=result_metadata)
