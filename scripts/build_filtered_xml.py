from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from xml_core import atomic_write, build_filtered_tree, fetch_bytes, load_json, save_json, sha256


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Kadıoğlu XML kaynağından seçili ürünleri üretir.")
    parser.add_argument("--source-file", help="İnternet yerine yerel XML dosyası kullanır.")
    parser.add_argument("--source-url", help="settings.json içindeki kaynak adresini geçersiz kılar.")
    parser.add_argument("--output", help="Çıktı XML yolunu geçersiz kılar.")
    parser.add_argument("--allow-missing", action="store_true", help="Eksik ürün olsa da çıktı üretir.")
    args = parser.parse_args()

    settings = load_json(PROJECT_ROOT / "config/settings.json")
    rules = load_json(PROJECT_ROOT / "config/products.json")
    source_url = args.source_url or settings["source_url"]
    output_path = resolve_project_path(args.output or settings["output_file"])
    status_path = resolve_project_path(settings["status_file"])

    if args.source_file:
        source_bytes = Path(args.source_file).read_bytes()
        source_label = str(Path(args.source_file).resolve())
    else:
        source_bytes = fetch_bytes(
            source_url,
            int(settings.get("request_timeout_seconds", 120)),
            int(settings.get("request_retries", 3)),
        )
        source_label = source_url

    tree, selected, missing = build_filtered_tree(source_bytes, rules, settings)
    fail_on_missing = bool(settings.get("fail_on_missing_products", True)) and not args.allow_missing
    if missing and fail_on_missing:
        missing_text = ", ".join(item.get("code") or item.get("barcode") or item.get("name", "?") for item in missing)
        raise RuntimeError(
            "Bazı ürünler kaynak XML'de bulunamadı. Eski XML korunuyor. Eksik: " + missing_text
        )
    if not selected:
        raise RuntimeError("Hiç ürün eşleşmedi. Boş XML yayımlanmadı.")

    buffer = io.BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True, short_empty_elements=True)
    output_bytes = buffer.getvalue()
    atomic_write(output_path, output_bytes)

    status = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source_label,
        "source_sha256": sha256(source_bytes),
        "output_sha256": sha256(output_bytes),
        "selected_product_count": len(selected),
        "missing_product_count": len(missing),
        "selected_products": selected,
        "missing_products": [
            {key: item.get(key, "") for key in ("name", "source_id", "code", "barcode", "producer_code")}
            for item in missing
        ],
    }
    save_json(status_path, status)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        raise SystemExit(1)
