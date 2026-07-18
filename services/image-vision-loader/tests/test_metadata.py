import unittest

from image_vision_loader.metadata import parse_filename_metadata


class MetadataTest(unittest.TestCase):
    def test_parse_scientific_figure_filename(self):
        self.assertEqual(
            parse_filename_metadata('[AB05]__figure_4.png'),
            {'paper_id': 'AB05', 'figure_no': '4'},
        )

    def test_metadata_parser_does_not_invent_values(self):
        self.assertEqual(parse_filename_metadata('microscopy.png'), {})
