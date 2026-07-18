import unittest
from unittest.mock import AsyncMock, patch

from image_vision_loader import main
from image_vision_loader.claude import ClaudeVisionError
from image_vision_loader.schema import VisionAnalysis


class ImageSignatureTest(unittest.TestCase):
    def test_accepts_supported_image_signatures(self):
        self.assertTrue(main._has_valid_signature(b'\xff\xd8\xffpayload', 'image/jpeg'))
        self.assertTrue(main._has_valid_signature(b'\x89PNG\r\n\x1a\npayload', 'image/png'))
        self.assertTrue(main._has_valid_signature(b'RIFF\x04\x00\x00\x00WEBPpayload', 'image/webp'))

    def test_rejects_mime_spoofing(self):
        self.assertFalse(main._has_valid_signature(b'not an image', 'image/png'))
        self.assertFalse(main._has_valid_signature(b'\x89PNG\r\n\x1a\npayload', 'image/jpeg'))


class VisionProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_falls_back_to_anthropic_after_open_webui_failure(self):
        fallback_result = {'caption': 'validated fallback'}
        with (
            patch.object(main, 'OPEN_WEBUI_API_KEY', 'local-key'),
            patch.object(main, 'ANTHROPIC_API_KEY', 'anthropic-key'),
            patch.object(
                main,
                'analyze_image_via_open_webui',
                AsyncMock(side_effect=ClaudeVisionError('forbidden')),
            ),
            patch.object(
                main,
                'analyze_image',
                AsyncMock(return_value=fallback_result),
            ),
        ):
            result, model = await main._analyze_with_fallback(
                image=b'image',
                media_type='image/png',
                filename='figure.png',
                metadata={},
            )
        self.assertEqual(result, fallback_result)
        self.assertEqual(model, main.ANTHROPIC_MODEL)

    async def test_reports_all_provider_failures(self):
        with (
            patch.object(main, 'OPEN_WEBUI_API_KEY', 'local-key'),
            patch.object(main, 'ANTHROPIC_API_KEY', 'anthropic-key'),
            patch.object(
                main,
                'analyze_image_via_open_webui',
                AsyncMock(side_effect=ClaudeVisionError('local failure')),
            ),
            patch.object(
                main,
                'analyze_image',
                AsyncMock(side_effect=ClaudeVisionError('remote failure')),
            ),
        ):
            with self.assertRaisesRegex(ClaudeVisionError, 'Open WebUI.*Anthropic'):
                await main._analyze_with_fallback(
                    image=b'image',
                    media_type='image/png',
                    filename='figure.png',
                    metadata={},
                )


class VisionSchemaTest(unittest.TestCase):
    def test_normalizes_single_text_values(self):
        analysis = VisionAnalysis.model_validate({'caption': 'figure', 'ocr': 'single label', 'trends': None})
        self.assertEqual(analysis.ocr, ['single label'])
        self.assertEqual(analysis.trends, [])
