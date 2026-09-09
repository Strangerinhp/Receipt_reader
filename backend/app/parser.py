from __future__ import annotations

import base64
import json
import mimetypes
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .schema import invoice_template, normalize_invoice_document
from .invoice_text import document_from_text, value_after_label as _value_after_label
from .pdf_reader import read_pdf, read_image


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _element_to_value(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or "").strip()

    result: dict[str, Any] = {}
    for child in children:
        key = _local_name(child.tag)
        value = _element_to_value(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value

    for name, value in element.attrib.items():
        result[f"@{_local_name(name)}"] = value
    return result


def parse_xml(payload: bytes) -> tuple[dict[str, Any], str]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"XML không hợp lệ: {exc}") from exc
    parsed = {_local_name(root.tag): _element_to_value(root)}
    text = payload.decode("utf-8-sig", errors="replace")
    return normalize_invoice_document(parsed), text


def parse_input(filename: str, content_type: str | None, payload: bytes, use_ocr: bool) -> dict[str, Any]:
    if not payload:
        raise ValueError("File rỗng.")
    suffix = Path(filename).suffix.lower()
    mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    warnings: list[str] = []

    if suffix == ".xml" or mime in {"application/xml", "text/xml"}:
        document, extracted_text = parse_xml(payload)
        parser_name = "XML"
        ocr_used = False
    elif suffix == ".json" or mime == "application/json":
        try:
            raw = json.loads(payload.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"JSON không hợp lệ: {exc}") from exc
        document = normalize_invoice_document(raw if isinstance(raw, dict) else {})
        extracted_text = json.dumps(raw, ensure_ascii=False, indent=2)
        parser_name = "JSON"
        ocr_used = False
    elif suffix == ".pdf" or mime == "application/pdf":
        document, extracted_text, warnings, ocr_used = read_pdf(payload, use_ocr)
        parser_name = "PDF bố cục + OCR" if ocr_used else "PDF bố cục và bảng"
    elif mime.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        if use_ocr:
            document, extracted_text, warnings, ocr_used = read_image(payload)
            parser_name = "OCR bố cục và bảng"
        else:
            extracted_text = ""
            parser_name = "Không OCR"
            ocr_used = False
            document = invoice_template()
            warnings.append("OCR đang tắt nên các trường của ảnh được để trống.")
    elif suffix in {".txt", ".csv"} or mime.startswith("text/"):
        extracted_text = payload.decode("utf-8-sig", errors="replace")
        parser_name = "Văn bản"
        ocr_used = False
        document = document_from_text(extracted_text)
    elif use_ocr:
        document, extracted_text, warnings, ocr_used = read_image(payload)
        parser_name = "OCR bố cục và bảng"
    else:
        extracted_text = ""
        parser_name = "Không xác định"
        ocr_used = False
        document = invoice_template()
        warnings.append("Định dạng đặc biệt chưa có bộ đọc; entry được tạo với các trường trống.")

    return {
        "filename": filename,
        "content_type": mime,
        "parser": parser_name,
        "ocr_enabled": bool(use_ocr),
        "ocr_used": ocr_used,
        "extracted_text": extracted_text,
        "document": document,
        "source_base64": base64.b64encode(payload).decode("ascii"),
        "warnings": warnings,
    }
