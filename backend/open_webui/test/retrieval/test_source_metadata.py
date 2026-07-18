import unittest

from open_webui.retrieval.source_identity import build_file_source_metadata


class SourceMetadataTest(unittest.TestCase):
    def test_preserves_scientific_identifiers(self):
        result = build_file_source_metadata(
            {
                'paper_id': 'RV04',
                'figure_no': '6',
                'doi': '10.1000/example',
                'image_file_id': 'image-file-id',
                'kind': 'vision_figure',
            },
            file_id='canonical-file-id',
            filename='[RV04]__figure_6.png',
        )

        self.assertEqual(result['paper_id'], 'RV04')
        self.assertEqual(result['figure_no'], '6')
        self.assertEqual(result['doi'], '10.1000/example')
        self.assertEqual(result['image_file_id'], 'image-file-id')
        self.assertEqual(result['kind'], 'vision_figure')

    def test_canonical_source_fields_cannot_be_overridden(self):
        result = build_file_source_metadata(
            {'file_id': 'wrong', 'name': 'wrong', 'source': 'wrong'},
            file_id='correct-id',
            filename='correct.md',
        )

        self.assertEqual(result['file_id'], 'correct-id')
        self.assertEqual(result['name'], 'correct.md')
        self.assertEqual(result['source'], 'correct.md')

    def test_handles_missing_metadata(self):
        result = build_file_source_metadata(
            None,
            file_id='file-id',
            filename='paper.md',
        )

        self.assertEqual(
            result,
            {'file_id': 'file-id', 'name': 'paper.md', 'source': 'paper.md'},
        )
