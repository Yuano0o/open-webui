import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / 'batch_upload_images_to_knowledge.py'
SPEC = importlib.util.spec_from_file_location('batch_upload_images', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BatchUploadImageTest(unittest.TestCase):
    def test_build_asset_uses_upload_bundle_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'collection_a' / 'upload_ready' / '_assets'
            figure_dir = root / 'PA01__10.1000_example.2024.001' / 'figures'
            figure_dir.mkdir(parents=True)
            image = figure_dir / '[PA01]__figure_2.png'
            image.write_bytes(b'png bytes')
            image.with_name('[PA01]__figure_2_caption.md').write_text(
                'Example figure caption', encoding='utf-8'
            )

            asset = MODULE.build_asset(image, root)

            self.assertEqual(asset.metadata['paper_id'], 'PA01')
            self.assertEqual(asset.metadata['doi'], '10.1000/example.2024.001')
            self.assertEqual(asset.metadata['figure_no'], '2')
            self.assertEqual(asset.metadata['caption'], 'Example figure caption')
            self.assertEqual(asset.metadata['asset_type'], 'figure')

    def test_table_markdown_is_used_as_searchable_caption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'collection_b' / 'upload_ready' / '_assets'
            table_dir = root / 'PB01__10.1000_example.2024.002' / 'tables'
            table_dir.mkdir(parents=True)
            image = table_dir / '[PB01]__table_1.png'
            image.write_bytes(b'png bytes')
            image.with_suffix('.md').write_text('| A | B |', encoding='utf-8')

            asset = MODULE.build_asset(image, root)

            self.assertEqual(asset.metadata['asset_type'], 'table')
            self.assertEqual(asset.metadata['asset_no'], '1')
            self.assertEqual(asset.metadata['caption'], '| A | B |')


if __name__ == '__main__':
    unittest.main()
