from pathlib import Path
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from xml_core import build_filtered_tree, load_json, local_name, matches
from product_spreadsheet import products_from_xlsx, products_to_xlsx, validate_products
from admin_server import Handler


FIXTURE_RULES = [
    {"enabled": True, "source_id": "524954", "barcode": "3501170818305", "images": ["https://example.com/extra.jpg"]},
    {"enabled": True, "barcode": "3026981382338", "images": []},
    {"enabled": True, "barcode": "3026982134219", "images": []},
    {"enabled": True, "barcode": "3026982133809", "images": []},
    {"enabled": True, "barcode": "3501177418331", "images": []},
    {"enabled": True, "barcode": "3501179860060", "images": []},
]


class FilterTests(unittest.TestCase):
    def test_only_six_products_and_extra_images(self):
        source = (ROOT / "tests/fixture.xml").read_bytes()
        settings = load_json(ROOT / "config/settings.json")
        rules = FIXTURE_RULES
        tree, selected, missing = build_filtered_tree(source, rules, settings)
        products = [n for n in tree.getroot() if local_name(n.tag) == "URUN"]
        self.assertEqual(6, len(products))
        self.assertEqual([], missing)
        self.assertEqual(6, len(selected))
        codes = {p.findtext("CODE") for p in products}
        self.assertNotIn("ISTENMEYEN", codes)
        self.assertTrue(products[0].findtext("RESIM2"))

    def test_excel_round_trip_preserves_products_and_images(self):
        rules = load_json(ROOT / "config/products.json")
        workbook = products_to_xlsx(rules, 16)
        imported = products_from_xlsx(workbook, 16)
        self.assertEqual(rules, imported)
        self.assertTrue(imported[0]["images"])

    def test_duplicate_active_identifier_is_rejected(self):
        products = [
            {"enabled": True, "name": "A", "barcode": "123", "images": []},
            {"enabled": True, "name": "B", "barcode": "123", "images": []},
        ]
        with self.assertRaisesRegex(ValueError, "iki kez"):
            validate_products(products)

    def test_duplicate_producer_code_is_allowed_with_unique_barcodes(self):
        products = [
            {"enabled": True, "name": "Mavi", "barcode": "111", "producer_code": "6030", "images": []},
            {"enabled": True, "name": "Siyah", "barcode": "222", "producer_code": "6030", "images": []},
        ]
        self.assertEqual(2, len(validate_products(products)))

    def test_duplicate_producer_code_without_stronger_identifier_is_rejected(self):
        products = [
            {"enabled": True, "name": "Mavi", "barcode": "111", "producer_code": "6030", "images": []},
            {"enabled": True, "name": "Siyah", "producer_code": "6030", "images": []},
        ]
        with self.assertRaisesRegex(ValueError, "benzersiz barkod"):
            validate_products(products)

    def test_barcode_has_priority_over_duplicate_producer_code(self):
        source_product = ET.fromstring(
            "<Urun><BARCODE>222</BARCODE><CODE>B</CODE><PRODUCERCODE>6030</PRODUCERCODE></Urun>"
        )
        self.assertFalse(matches(source_product, {"barcode": "111", "producer_code": "6030"}))
        self.assertTrue(matches(source_product, {"barcode": "222", "producer_code": "6030"}))

    def test_admin_excel_download_and_import_endpoints(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(base_url + "/api/products.xlsx", timeout=5) as response:
                workbook = response.read()
                self.assertEqual(200, response.status)
                self.assertIn("spreadsheetml", response.headers["Content-Type"])
            request = urllib.request.Request(
                base_url + "/api/import-xlsx",
                data=workbook,
                method="POST",
                headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(len(load_json(ROOT / "config/products.json")), payload["count"])
                self.assertEqual("3501170818305", payload["products"][0]["barcode"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
