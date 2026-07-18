import unittest
from types import SimpleNamespace

from open_webui.retrieval.source_identity import add_source_identity_to_chunks


class ChunkIdentityTest(unittest.TestCase):
    def test_prefixes_every_chunk_with_its_source_name(self):
        docs = [
            SimpleNamespace(page_content='first', metadata={'name': '[RV04]__paper.md'}),
            SimpleNamespace(page_content='second', metadata={'name': '[RV04]__paper.md'}),
        ]

        result = add_source_identity_to_chunks(docs)

        self.assertTrue(all(doc.page_content.startswith('Document: [RV04]__paper.md\n') for doc in result))

    def test_prefixes_structured_identifiers_on_every_chunk(self):
        doc = SimpleNamespace(
            page_content='results',
            metadata={
                'name': 'figure.png',
                'paper_id': 'RV04',
                'figure_no': '6',
                'doi': '10.1000/example',
            },
        )

        result = add_source_identity_to_chunks([doc])

        self.assertTrue(result[0].page_content.startswith('Document: figure.png\n'))
        self.assertIn('paper_id: RV04\n', result[0].page_content)
        self.assertIn('figure_no: 6\n', result[0].page_content)
        self.assertIn('DOI: 10.1000/example\n', result[0].page_content)

    def test_is_idempotent(self):
        doc = SimpleNamespace(
            page_content='Document: paper.md\ncontent',
            metadata={'name': 'paper.md'},
        )

        result = add_source_identity_to_chunks([doc])

        self.assertEqual(result[0].page_content.count('Document: paper.md'), 1)

    def test_adds_only_missing_identity_lines(self):
        doc = SimpleNamespace(
            page_content='Document: paper.md\ncontent',
            metadata={'name': 'paper.md', 'paper_id': 'RV04'},
        )

        result = add_source_identity_to_chunks([doc])

        self.assertEqual(result[0].page_content.count('Document: paper.md'), 1)
        self.assertEqual(result[0].page_content.count('paper_id: RV04'), 1)

    def test_leaves_anonymous_chunks_unchanged(self):
        doc = SimpleNamespace(page_content='content', metadata={})

        result = add_source_identity_to_chunks([doc])

        self.assertEqual(result[0].page_content, 'content')
