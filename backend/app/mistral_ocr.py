"""Mistral OCR engine and Markdown-table conversion."""
from __future__ import annotations

import base64
import html
import os
import re

from .pdf_reader import _finish


def validate_engine(ocr_engine: str) -> None:
    if ocr_engine not in {"tesseract", "mistral"}:
        raise ValueError("OCR engine phải là tesseract hoặc mistral.")


def _table_cells(line: str) -> list[str]:
    line = line.strip().strip("|")
    cells = []
    for cell in re.split(r"(?<!\\)\|", line):
        cell = re.sub(r"<br\s*/?>", "\n", cell, flags=re.I)
        cell = re.sub(r"</?(?:b|strong|i|em)>", "", cell, flags=re.I)
        cell = re.sub(r"(?<!\\)[*_]{1,3}", "", cell)
        cells.append(html.unescape(cell.replace(r"\|", "|")).strip())
    return cells


def markdown_tables(markdown: str, page_number: int) -> list[dict]:
    """Extract GitHub-style Markdown tables returned by Mistral OCR."""
    lines = markdown.splitlines()
    tables = []
    index = 0
    while index + 1 < len(lines):
        header = _table_cells(lines[index]) if "|" in lines[index] else []
        separator = _table_cells(lines[index + 1]) if "|" in lines[index + 1] else []
        if (len(header) >= 2 and len(header) == len(separator) and
                all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separator)):
            rows = [header]
            index += 2
            while index < len(lines) and "|" in lines[index]:
                row = _table_cells(lines[index])
                if len(row) != len(header):
                    break
                rows.append(row)
                index += 1
            tables.append({"page": page_number, "method": "Mistral OCR table", "rows": rows})
            continue
        index += 1
    return tables


def readable_text(markdown: str) -> str:
    """Remove presentation-only Markdown while retaining invoice labels/values."""
    text = re.sub(r"!\[[^]]*]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}[ \t]+", "", text, flags=re.M)
    text = re.sub(r"(?<!\\)[*_]{1,3}", "", text)
    return text.replace(r"\|", "|").strip()


def read_mistral(payload: bytes, mime: str, progress=None):
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Thiếu MISTRAL_API_KEY trên máy chủ. Xem README để cấu hình Mistral OCR.")
    try:
        from mistralai.client import Mistral
    except ImportError:
        raise RuntimeError("Thiếu SDK Mistral. Hãy cài lại requirements của backend.") from None

    is_pdf = mime == "application/pdf"
    if not is_pdf and len(payload) > 20 * 1024 * 1024:
        raise ValueError("Ảnh vượt giới hạn 20 MB của Mistral OCR.")
    kind = "document_url" if is_pdf else "image_url"
    field = "document_url" if is_pdf else "image_url"
    encoded = base64.b64encode(payload).decode("ascii")
    document = {"type": kind, field: f"data:{mime};base64,{encoded}"}
    if progress:
        progress("Đang gửi tài liệu tới Mistral OCR...")
    try:
        with Mistral(api_key=api_key, timeout_ms=120_000) as client:
            response = client.ocr.process(
                model=os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest"),
                document=document,
                table_format="markdown",
                include_image_base64=False,
            )
    except Exception:
        # Avoid leaking request/authentication details returned by the SDK.
        raise RuntimeError("Mistral OCR không xử lý được tài liệu. Kiểm tra API key, kết nối, quota và billing.") from None

    pages = sorted(response.pages or [], key=lambda page: page.index)
    if not pages:
        raise RuntimeError("Mistral OCR không trả về trang kết quả nào.")
    texts, tables, warnings = [], [], []
    for offset, page in enumerate(pages, 1):
        number = int(page.index) + 1
        markdown = page.markdown or ""
        page_tables = []
        for table in getattr(page, "tables", None) or []:
            content = table.content or ""
            page_tables.extend(markdown_tables(content, number))
            if content and content not in markdown:
                markdown += "\n\n" + content
        texts.append(readable_text(markdown))
        tables.extend(page_tables or markdown_tables(markdown, number))
        if progress:
            progress(f"Đã nhận kết quả Mistral trang {offset}/{len(pages)}...")
        if not markdown.strip():
            warnings.append(f"Trang {number}: Mistral OCR không nhận được văn bản.")
    warnings.append("Tài liệu được đọc bằng Mistral OCR; cần đối chiếu chữ, bảng và số tiền với file gốc.")
    return _finish(texts, tables, warnings, True)
