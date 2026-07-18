from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import unquote

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import ValidationError

from .claude import ClaudeVisionError, analyze_image, analyze_image_via_open_webui
from .metadata import parse_filename_metadata
from .schema import VisionAnalysis

SUPPORTED_MEDIA_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_BYTES = int(os.getenv('VISION_MAX_IMAGE_BYTES', str(10 * 1024 * 1024)))
SERVICE_API_KEY = os.getenv('VISION_LOADER_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_VISION_MODEL', 'claude-sonnet-4-6')
ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
OPEN_WEBUI_API_KEY = os.getenv('OPEN_WEBUI_API_KEY', '')
OPEN_WEBUI_BASE_URL = os.getenv('OPEN_WEBUI_BASE_URL', 'http://127.0.0.1:8080')
OPEN_WEBUI_VISION_MODEL = os.getenv('OPEN_WEBUI_VISION_MODEL', 'claude-sonnet-5')

app = FastAPI(title='Open WebUI Image Vision Loader', version='0.1.0')


def _has_valid_signature(image: bytes, media_type: str) -> bool:
    return {
        'image/jpeg': image.startswith(b'\xff\xd8\xff'),
        'image/png': image.startswith(b'\x89PNG\r\n\x1a\n'),
        'image/webp': (len(image) >= 12 and image.startswith(b'RIFF') and image[8:12] == b'WEBP'),
    }.get(media_type, False)


def _render_searchable_markdown(filename: str, metadata: dict[str, Any], analysis: dict[str, Any]) -> str:
    lines = [
        '# Scientific figure',
        f'- filename: {filename}',
        f'- paper_id: {metadata.get("paper_id", "")}',
        f'- figure_no: {metadata.get("figure_no", "")}',
        f'- DOI: {metadata.get("doi", "")}',
        f'- figure_type: {analysis.get("figure_type", "other")}',
        '',
        '## Searchable visual description',
        str(analysis.get('caption', '')),
        '',
        '## OCR',
        '\n'.join(f'- {item}' for item in analysis.get('ocr', []) if item),
        '',
        '## Panels',
        '\n'.join(
            f'- {item.get("label", "")}: {item.get("description", "")} ({item.get("location", "")})'
            for item in analysis.get('panels', [])
            if isinstance(item, dict)
        ),
        '',
        '## Axes and trends',
        json.dumps(analysis.get('axes', {}), ensure_ascii=False),
        '\n'.join(f'- {item}' for item in analysis.get('trends', []) if item),
        '',
        '## Labels',
        '\n'.join(f'- {item}' for item in analysis.get('labels', []) if item),
        '',
        '## Blot or gel lanes',
        '\n'.join(
            f'- panel={item.get("panel", "")}; lane={item.get("lane", "")}; '
            f'label={item.get("label", "")}; observation={item.get("observation", "")}'
            for item in analysis.get('blot_lanes', [])
            if isinstance(item, dict)
        ),
        '',
        '## Interpretation',
        str(analysis.get('scientific_interpretation', '')),
        '',
        '## Uncertainties',
        '\n'.join(f'- {item}' for item in analysis.get('uncertainties', []) if item),
    ]
    return '\n'.join(lines).strip()


async def _analyze_with_fallback(
    *,
    image: bytes,
    media_type: str,
    filename: str,
    metadata: dict[str, str],
) -> tuple[dict[str, Any], str]:
    """Prefer the configured Open WebUI model, then use Anthropic if available."""
    provider_errors: list[str] = []
    if OPEN_WEBUI_API_KEY:
        try:
            return (
                await analyze_image_via_open_webui(
                    image=image,
                    media_type=media_type,
                    filename=filename,
                    metadata=metadata,
                    api_key=OPEN_WEBUI_API_KEY,
                    model=OPEN_WEBUI_VISION_MODEL,
                    base_url=OPEN_WEBUI_BASE_URL,
                ),
                OPEN_WEBUI_VISION_MODEL,
            )
        except ClaudeVisionError as exc:
            provider_errors.append(f'Open WebUI: {exc}')

    if ANTHROPIC_API_KEY:
        try:
            return (
                await analyze_image(
                    image=image,
                    media_type=media_type,
                    filename=filename,
                    metadata=metadata,
                    api_key=ANTHROPIC_API_KEY,
                    model=ANTHROPIC_MODEL,
                    base_url=ANTHROPIC_BASE_URL,
                ),
                ANTHROPIC_MODEL,
            )
        except ClaudeVisionError as exc:
            provider_errors.append(f'Anthropic: {exc}')

    raise ClaudeVisionError('; '.join(provider_errors) or 'No vision provider is available')


async def _read_validated_image(request: Request, content_type: str | None) -> tuple[bytes, str]:
    media_type = (content_type or '').split(';', 1)[0].strip().lower()
    if media_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(status_code=415, detail=f'Unsupported image type: {media_type}')
    image = await request.body()
    if not image:
        raise HTTPException(status_code=400, detail='Empty image')
    if len(image) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f'Image exceeds {MAX_IMAGE_BYTES} bytes')
    if not _has_valid_signature(image, media_type):
        raise HTTPException(
            status_code=415,
            detail=f'File signature does not match {media_type}',
        )
    return image, media_type


@app.get('/health')
async def health() -> dict[str, bool]:
    return {'ok': True}


@app.put('/process')
async def process_image(
    request: Request,
    authorization: str | None = Header(default=None),
    content_type: str | None = Header(default=None),
    x_filename: str = Header(default='image'),
    x_paper_id: str | None = Header(default=None),
    x_figure_no: str | None = Header(default=None),
    x_doi: str | None = Header(default=None),
):
    if SERVICE_API_KEY and authorization != f'Bearer {SERVICE_API_KEY}':
        raise HTTPException(status_code=401, detail='Invalid loader API key')
    image, media_type = await _read_validated_image(request, content_type)
    if not OPEN_WEBUI_API_KEY and not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail='Neither OPEN_WEBUI_API_KEY nor ANTHROPIC_API_KEY is configured',
        )

    filename = unquote(x_filename)
    metadata = parse_filename_metadata(filename)
    for key, value in {'paper_id': x_paper_id, 'figure_no': x_figure_no, 'doi': x_doi}.items():
        if value:
            metadata[key] = value
    try:
        raw_analysis, vision_model = await _analyze_with_fallback(
            image=image,
            media_type=media_type,
            filename=filename,
            metadata=metadata,
        )
    except ClaudeVisionError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    try:
        analysis = VisionAnalysis.model_validate(raw_analysis).model_dump()
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f'Vision provider returned an invalid analysis schema: {exc.error_count()} validation error(s)',
        ) from exc

    return {
        'page_content': _render_searchable_markdown(filename, metadata, analysis),
        'metadata': {
            'kind': 'vision_figure',
            'paper_id': metadata.get('paper_id', ''),
            'figure_no': metadata.get('figure_no', ''),
            'doi': metadata.get('doi', ''),
            'vision_model': vision_model,
            'vision_schema_version': 1,
            'vision_analysis': analysis,
        },
    }


def run() -> None:
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('PORT', '8765')))
