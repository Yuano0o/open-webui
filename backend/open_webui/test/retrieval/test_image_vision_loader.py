import unittest

from open_webui.retrieval.loaders.image_vision import (
    ImageVisionLoaderError,
    _validate_signature,
)


class ImageVisionLoaderTest(unittest.TestCase):
    def test_accepts_supported_signatures(self):
        _validate_signature(b'\xff\xd8\xffpayload', 'image/jpeg')
        _validate_signature(b'\x89PNG\r\n\x1a\npayload', 'image/png')
        _validate_signature(b'RIFF\x04\x00\x00\x00WEBPpayload', 'image/webp')

    def test_rejects_mime_spoofing(self):
        with self.assertRaises(ImageVisionLoaderError):
            _validate_signature(b'not an image', 'image/png')
