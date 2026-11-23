from __future__ import annotations

import copy
import hashlib
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


IDENTIFIER_TAGS = {
    "source_id": ("ID",),
    "code": ("CODE",),
    "barcode": (
        "BARCODE",
        "BARKOD",
        "BARKODNO",
        "BIRIM_1_BARCODE",
        "BIRIM_2_BARCODE",
        "BIRIM_3_BARCODE",
        "BIRIM_4_BARCODE",
    ),
    "producer_code": ("PRODUCERCODE", "URETICIKODU", "MODEL_KODU"),
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].upper()


def normalized(value: Any) -> str:
    return str(value or "").strip().casefold()


def node_texts(product: ET.Element) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    for node in product.iter():
        text = normalized(node.text)
        if text:
            values.setdefault(local_name(node.tag), set()).add(text)
    return values


def first_text(product: ET.Element, names: Iterable[str]) -> str:
    wanted = {name.upper() for name in names}
    for node in product.iter():
        if local_name(node.tag) in wanted and node.text:
            return node.text.strip()
    return ""


def product_summary(product: ET.Element) -> dict[str, str]:
    return {
        "source_id": first_text(product, IDENTIFIER_TAGS["source_id"]),
        "code": first_text(product, IDENTIFIER_TAGS["code"]),
        "barcode": first_text(product, IDENTIFIER_TAGS["barcode"]),
        "producer_code": first_text(product, IDENTIFIER_TAGS["producer_code"]),
        "name": first_text(product, ("NAME", "ADI", "URUNADI")),
        "brand": first_text(product, ("MARKA", "BRAND")),
        "top_category": first_text(product, ("UST_KAT",)),
        "middle_category": first_text(product, ("ORTA_KAT",)),
        "category": first_text(product, ("ALT_KAT", "STGRPCODE")),
        "stock": first_text(product, ("STOK", "STOCK")),
    }


def matches(product: ET.Element, rule: dict[str, Any]) -> bool:
    values = node_texts(product)
    for field, tags in IDENTIFIER_TAGS.items():
        expected = normalized(rule.get(field))
        if not expected:
            continue
        for tag in tags:
            if expected in values.get(tag.upper(), set()):
                return True
    return False


def set_direct_child(product: ET.Element, tag_name: str, value: str) -> None:
    wanted = tag_name.upper()
    for node in list(product):
        if local_name(node.tag) == wanted:
            node.text = value
            return
    node = ET.Element(tag_name)
    node.text = value
    product.append(node)


def enrich_images(product: ET.Element, rule: dict[str, Any], prefix: str, max_images: int) -> None:
    urls = [str(url).strip() for url in rule.get("images", []) if str(url).strip()]
    for index, url in enumerate(urls, start=2):
        if index > max_images:
            break
        set_direct_child(product, f"{prefix}{index}", url)


def find_products(root: ET.Element, product_tag: str) -> list[ET.Element]:
    wanted = product_tag.upper()
    return [node for node in root.iter() if local_name(node.tag) == wanted]


def build_filtered_tree(
    source_bytes: bytes,
    rules: list[dict[str, Any]],
    settings: dict[str, Any],
) -> tuple[ET.ElementTree, list[dict[str, str]], list[dict[str, Any]]]:
    source_root = ET.fromstring(source_bytes)
    product_tag = settings.get("product_tag", "Urun")
    products = find_products(source_root, product_tag)
    enabled_rules = [rule for rule in rules if rule.get("enabled", True)]
    selected: list[ET.Element] = []
    selected_summaries: list[dict[str, str]] = []
    missing: list[dict[str, Any]] = []
    used_product_ids: set[int] = set()

    for rule in enabled_rules:
        hit = next((p for p in products if id(p) not in used_product_ids and matches(p, rule)), None)
        if hit is None:
            missing.append(rule)
            continue
        used_product_ids.add(id(hit))
        cloned = copy.deepcopy(hit)
        enrich_images(
            cloned,
            rule,
            str(settings.get("image_tag_prefix", "RESIM")),
            int(settings.get("max_images", 16)),
        )
        selected.append(cloned)
        selected_summaries.append(product_summary(cloned))

    new_root = ET.Element(source_root.tag, source_root.attrib)
    if settings.get("preserve_non_product_nodes", True):
        for child in list(source_root):
            if local_name(child.tag) != product_tag.upper():
                new_root.append(copy.deepcopy(child))
    for product in selected:
        new_root.append(product)

    if hasattr(ET, "indent"):
        ET.indent(new_root, space="  ")
    return ET.ElementTree(new_root), selected_summaries, missing


def fetch_bytes(url: str, timeout: int, retries: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FZD-XML-Filter/1.0 (+https://github.com/)",
            "Accept": "application/xml,text/xml,*/*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # network errors differ by platform
            last_error = exc
            if attempt < retries:
                time.sleep(attempt * 3)
    raise RuntimeError(f"Kaynak XML indirilemedi: {last_error}")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> None:
    data = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    atomic_write(path, data)
