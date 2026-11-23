from __future__ import annotations

import io
import posixpath
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from typing import Any
from xml.sax.saxutils import escape


MAX_IMPORT_ROWS = 10_000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

BASE_COLUMNS = (
    ("enabled", "Aktif"),
    ("name", "Ürün Adı"),
    ("code", "Ürün Kodu"),
    ("barcode", "Barkod"),
    ("producer_code", "Üretici Kodu"),
    ("source_id", "Kaynak ID"),
)
IDENTIFIER_FIELDS = ("barcode", "producer_code", "code", "source_id")
UNIQUE_IDENTIFIER_FIELDS = ("barcode", "code", "source_id")


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _normalize_header(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().translate(str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ç": "c", "ö": "o", "ü": "u"}))
    return re.sub(r"[^a-z0-9]+", "", text)


HEADER_ALIASES = {
    "aktif": "enabled",
    "enabled": "enabled",
    "urunadi": "name",
    "name": "name",
    "urunkodu": "code",
    "code": "code",
    "barkod": "barcode",
    "barcode": "barcode",
    "ureticikodu": "producer_code",
    "producercode": "producer_code",
    "kaynakid": "source_id",
    "sourceid": "source_id",
}


def _parse_enabled(value: Any) -> bool:
    normalized = _normalize_header(value)
    if normalized in {"", "1", "true", "evet", "yes", "aktif"}:
        return True
    if normalized in {"0", "false", "hayir", "no", "pasif"}:
        return False
    raise ValueError(f"Aktif alanı Evet/Hayır olmalı; gelen değer: {value!r}")


def validate_products(products: list[dict[str, Any]], max_images: int = 16) -> list[dict[str, Any]]:
    if not isinstance(products, list):
        raise ValueError("Ürün listesi geçersiz.")
    if len(products) > MAX_IMPORT_ROWS:
        raise ValueError(f"En fazla {MAX_IMPORT_ROWS} ürün içe aktarılabilir.")

    cleaned: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], int] = {}
    labels = dict(BASE_COLUMNS)
    for row_number, item in enumerate(products, start=2):
        if not isinstance(item, dict):
            raise ValueError(f"{row_number}. satır geçersiz.")
        product = {
            "enabled": bool(item.get("enabled", True)),
            "name": str(item.get("name", "") or "").strip(),
            "source_id": str(item.get("source_id", "") or "").strip(),
            "code": str(item.get("code", "") or "").strip(),
            "barcode": str(item.get("barcode", "") or "").strip(),
            "producer_code": str(item.get("producer_code", "") or "").strip(),
            "images": [
                str(url).strip()
                for url in (item.get("images") or [])[:max_images]
                if str(url).strip()
            ],
        }
        if product["enabled"] and not any(product[field] for field in IDENTIFIER_FIELDS):
            raise ValueError(
                f"{row_number}. satırdaki aktif ürünün barkod, üretici kodu, ürün kodu "
                "veya kaynak ID alanlarından en az biri dolu olmalı."
            )
        if product["enabled"]:
            for field in UNIQUE_IDENTIFIER_FIELDS:
                value = product[field].casefold()
                if not value:
                    continue
                key = (field, value)
                if key in seen:
                    raise ValueError(
                        f"{row_number}. satırdaki {labels[field]} iki kez kullanılmış; "
                        f"aynı değer {seen[key]}. satırda da var: {product[field]}"
                    )
                seen[key] = row_number
        cleaned.append(product)
    return cleaned


def products_to_xlsx(products: list[dict[str, Any]], max_images: int = 16) -> bytes:
    products = validate_products(products, max_images)
    headers = [label for _, label in BASE_COLUMNS] + [f"Görsel {index}" for index in range(1, max_images + 1)]
    rows: list[list[str]] = [headers]
    for product in products:
        rows.append([
            "Evet" if product["enabled"] else "Hayır",
            product["name"],
            product["code"],
            product["barcode"],
            product["producer_code"],
            product["source_id"],
            *product["images"],
            *([""] * (max_images - len(product["images"]))),
        ])

    shared_values: list[str] = []
    shared_indexes: dict[str, int] = {}
    for row in rows:
        for value in row:
            text = str(value)
            if text not in shared_indexes:
                shared_indexes[text] = len(shared_values)
                shared_values.append(text)

    sheet_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row, start=1):
            if row_index > 1 and not value:
                continue
            reference = f"{_column_name(column_index)}{row_index}"
            style = 1 if row_index == 1 else 2
            cells.append(f'<c r="{reference}" t="str" s="{style}"><v>{escape(str(value))}</v></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    last_column = _column_name(len(headers))
    last_row = max(1, len(rows))
    worksheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:{last_column}{last_row}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="18"/>
  <cols><col min="1" max="1" width="10" customWidth="1"/><col min="2" max="2" width="46" customWidth="1"/><col min="3" max="6" width="20" customWidth="1"/><col min="7" max="{len(headers)}" width="42" customWidth="1"/></cols>
  <sheetData>{''.join(sheet_rows)}</sheetData>
  <autoFilter ref="A1:{last_column}{last_row}"/>
</worksheet>'''

    files = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
        "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Ürünler" sheetId="1" r:id="rId1"/></sheets></workbook>''',
        "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>''',
        "xl/styles.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1268D3"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="2"><border/><border><bottom style="thin"><color rgb="FFDCE2EC"/></bottom></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="49" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="49" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>''',
        "xl/sharedStrings.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{sum(len(row) for row in rows)}" uniqueCount="{len(shared_values)}">'
            + "".join(f'<si><t xml:space="preserve">{escape(value)}</t></si>' for value in shared_values)
            + "</sst>"
        ),
        "xl/worksheets/sheet1.xml": worksheet,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode("utf-8"))
    return output.getvalue()


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter() if node.tag.endswith("}t")) for item in root]


def _first_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    first_sheet = next(node for node in workbook.iter() if node.tag.endswith("}sheet"))
    relation_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target = next(node.attrib["Target"] for node in relationships if node.attrib.get("Id") == relation_id)
    return target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter() if node.tag.endswith("}t"))
    value_node = next((node for node in cell if node.tag.endswith("}v")), None)
    value = value_node.text if value_node is not None and value_node.text is not None else ""
    if cell_type == "s" and value:
        return shared_strings[int(value)]
    if cell_type == "b":
        return "Evet" if value == "1" else "Hayır"
    return value


def products_from_xlsx(data: bytes, max_images: int = 16) -> list[dict[str, Any]]:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Excel dosyası en fazla 10 MB olabilir.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("Geçerli bir .xlsx dosyası seçin.") from exc

    with archive:
        if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
            raise ValueError("Excel dosyasının açılmış boyutu çok büyük.")
        try:
            root = ET.fromstring(archive.read(_first_sheet_path(archive)))
            shared_strings = _read_shared_strings(archive)
        except (KeyError, StopIteration, ET.ParseError, ValueError) as exc:
            raise ValueError("Excel dosyasındaki ilk çalışma sayfası okunamadı.") from exc

    rows: list[dict[int, str]] = []
    for row in (node for node in root.iter() if node.tag.endswith("}row")):
        values: dict[int, str] = {}
        for cell in (node for node in row if node.tag.endswith("}c")):
            match = re.match(r"([A-Z]+)", cell.attrib.get("r", "").upper())
            if not match:
                continue
            column = 0
            for char in match.group(1):
                column = column * 26 + ord(char) - 64
            values[column] = _cell_value(cell, shared_strings).strip()
        rows.append(values)
        if len(rows) > MAX_IMPORT_ROWS + 1:
            raise ValueError(f"Excel dosyası en fazla {MAX_IMPORT_ROWS} ürün satırı içerebilir.")
    if not rows:
        raise ValueError("Excel dosyasında satır bulunamadı.")

    header_map: dict[int, tuple[str, int | None]] = {}
    for column, header in rows[0].items():
        normalized = _normalize_header(header)
        if normalized in HEADER_ALIASES:
            header_map[column] = (HEADER_ALIASES[normalized], None)
            continue
        image_match = re.fullmatch(r"(?:gorsel|resim|image)(\d+)", normalized)
        if image_match and 1 <= int(image_match.group(1)) <= max_images:
            header_map[column] = ("images", int(image_match.group(1)))
    required = {field for field, _ in BASE_COLUMNS}
    present = {field for field, _ in header_map.values()}
    missing_headers = [label for field, label in BASE_COLUMNS if field not in present and field in required]
    if missing_headers:
        raise ValueError("Eksik Excel sütunları: " + ", ".join(missing_headers))

    products: list[dict[str, Any]] = []
    for row_index, values in enumerate(rows[1:], start=2):
        if not any(str(value).strip() for value in values.values()):
            continue
        product: dict[str, Any] = {
            "enabled": True, "name": "", "code": "", "barcode": "",
            "producer_code": "", "source_id": "", "images": [],
        }
        indexed_images: dict[int, str] = {}
        for column, (field, image_index) in header_map.items():
            value = values.get(column, "").strip()
            if field == "enabled":
                try:
                    product[field] = _parse_enabled(value)
                except ValueError as exc:
                    raise ValueError(f"{row_index}. satır: {exc}") from exc
            elif field == "images" and image_index is not None:
                if value:
                    indexed_images[image_index] = value
            else:
                product[field] = value
        product["images"] = [indexed_images[index] for index in sorted(indexed_images)]
        products.append(product)
    if not products:
        raise ValueError("Excel dosyasında içe aktarılacak ürün bulunamadı.")
    return validate_products(products, max_images)