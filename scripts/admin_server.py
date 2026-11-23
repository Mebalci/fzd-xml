from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from xml_core import fetch_bytes, find_products, load_json, product_summary, save_json
from product_spreadsheet import (
    MAX_UPLOAD_BYTES,
    products_from_xlsx,
    products_to_xlsx,
    validate_products,
)
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ADMIN_DIR = ROOT / "admin"
PRODUCTS_FILE = ROOT / "config/products.json"
SETTINGS_FILE = ROOT / "config/settings.json"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ADMIN_DIR), **kwargs)

    def send_json(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_bytes(self, data, content_type, filename):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            status_file = ROOT / load_json(SETTINGS_FILE)["status_file"]
            self.send_json({
                "products": load_json(PRODUCTS_FILE),
                "settings": load_json(SETTINGS_FILE),
                "status": load_json(status_file) if status_file.exists() else None,
            })
            return
        if parsed.path == "/api/source-products":
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip().casefold()
            settings = load_json(SETTINGS_FILE)
            source = fetch_bytes(
                settings["source_url"],
                int(settings.get("request_timeout_seconds", 120)),
                int(settings.get("request_retries", 3)),
            )
            root = ET.fromstring(source)
            items = [product_summary(p) for p in find_products(root, settings.get("product_tag", "Urun"))]
            if query:
                items = [item for item in items if query in " ".join(item.values()).casefold()]
            self.send_json({"count": len(items), "items": items[:250]})
            return
        if parsed.path == "/api/products.xlsx":
            settings = load_json(SETTINGS_FILE)
            data = products_to_xlsx(
                load_json(PRODUCTS_FILE),
                int(settings.get("max_images", 16)),
            )
            self.send_bytes(
                data,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "fzd-urunler.xlsx",
            )
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/products":
            payload = self.read_json()
            products = payload.get("products")
            if not isinstance(products, list):
                self.send_json({"ok": False, "error": "products listesi gerekli"}, 400)
                return
            try:
                settings = load_json(SETTINGS_FILE)
                products = validate_products(products, int(settings.get("max_images", 16)))
                save_json(PRODUCTS_FILE, products)
                self.send_json({"ok": True, "count": len(products)})
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
            return
        if self.path == "/api/import-xlsx":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_UPLOAD_BYTES:
                    raise ValueError("Excel dosyası boş veya 10 MB sınırını aşıyor.")
                settings = load_json(SETTINGS_FILE)
                products = products_from_xlsx(
                    self.rfile.read(length),
                    int(settings.get("max_images", 16)),
                )
                self.send_json({"ok": True, "count": len(products), "products": products})
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
            return
        if self.path == "/api/build":
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts/build_filtered_xml.py")],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=240,
            )
            self.send_json({
                "ok": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }, 200 if completed.returncode == 0 else 500)
            return
        self.send_json({"ok": False, "error": "Bilinmeyen işlem"}, 404)


if __name__ == "__main__":
    host, port = "127.0.0.1", 8765
    print(f"FZD XML yönetim paneli: http://{host}:{port}")
    print("Kapatmak için Ctrl+C")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
