from pathlib import Path
import json
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from xml_core import build_filtered_tree, load_json, local_name


class FilterTests(unittest.TestCase):
    def test_only_six_products_and_extra_images(self):
        source = (ROOT / "tests/fixture.xml").read_bytes()
        settings = load_json(ROOT / "config/settings.json")
        rules = load_json(ROOT / "config/products.json")
        tree, selected, missing = build_filtered_tree(source, rules, settings)
        products = [n for n in tree.getroot() if local_name(n.tag) == "URUN"]
        self.assertEqual(6, len(products))
        self.assertEqual([], missing)
        self.assertEqual(6, len(selected))
        codes = {p.findtext("CODE") for p in products}
        self.assertNotIn("ISTENMEYEN", codes)
        self.assertTrue(products[0].findtext("RESIM2"))


if __name__ == "__main__":
    unittest.main()
