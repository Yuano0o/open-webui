from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from .prompt import SYSTEM_PROMPT, build_user_prompt


class ClaudeVisionError(RuntimeError):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith('```'):
        text = text.removeprefix('```json').removeprefix('```')
        text = text.removesuffix('```').strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ClaudeVisionError('Claude returned invalid JSON') from exc
    if not isinstance(value, dict):
        raise ClaudeVisionError('Claude vision response must be a JSON object')
    return value


async def analyze_image(
    *,
    image: bytes,
    media_type: str,
    filename: str,
    metadata: dict[str, str],
    api_key: str,
    model: str,
    base_url: str = 'https://api.anthropic.com',
    timeout_seconds: float = 120,
) -> dict[str, Any]:
    payload = {
        'model': model,
        'max_tokens': 2400,
        'temperature': 0,
        'system': SYSTEM_PROMPT,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': base64.b64encode(image).decode('ascii'),
                        },
                    },
                    {'type': 'text', 'text': build_user_prompt(filename, metadata)},
                ],
            }
        ],
    }
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds) as client:
        response = await client.post('/v1/messages', headers=headers, json=payload)
    if response.is_error:
        raise ClaudeVisionError(f'Claude API failed with HTTP {response.status_code}: {response.text[:500]}')
    data = response.json()
    text = ''.join(block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text')
    if not text:
        raise ClaudeVisionError('Claude returned no text content')
    return _extract_json(text)


async def analyze_image_via_open_webui(
    *,
    image: bytes,
    media_type: str,
    filename: str,
    metadata: dict[str, str],
    api_key: str,
    model: str,
    base_url: str = 'http://127.0.0.1:8080',
    timeout_seconds: float = 180,
) -> dict[str, Any]:
    """Use an existing Open WebUI model connection for vision analysis."""
    payload = {
        'model': model,
        'stream': False,
        'temperature': 0,
        'max_tokens': 2400,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {'url': (f'data:{media_type};base64,{base64.b64encode(image).decode("ascii")}')},
                    },
                    {'type': 'text', 'text': build_user_prompt(filename, metadata)},
                ],
            },
        ],
    }
    headers = {
        'authorization': f'Bearer {api_key}',
        'content-type': 'application/json',
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds) as client:
        response = await client.post('/api/v1/chat/completions', headers=headers, json=payload)
    if response.is_error:
        raise ClaudeVisionError(
            f'Open WebUI vision call failed with HTTP {response.status_code}: {response.text[:500]}'
        )
    data = response.json()
    content = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
    if isinstance(content, list):
        text = ''.join(
            part.get('text', '') for part in content if isinstance(part, dict) and part.get('type') == 'text'
        )
    else:
        text = str(content)
    if not text:
        raise ClaudeVisionError('Open WebUI vision model returned no text content')
    return _extract_json(text)
