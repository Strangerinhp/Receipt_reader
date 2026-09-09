"""Map geometric invoice tables to the existing XML-shaped document."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import re

from .invoice_text import compact, fold_accents
from .schema import ITEM_FIELDS


def decimal_value(value: str) -> Decimal | None:
    """Vietnamese display numbers only; never silently remove arbitrary characters."""
    value = compact(value).replace(" ", "")
    if not value:
        return None
    if not re.fullmatch(r"[-+]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?", value):
        return None
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def header_columns(row: list[str]) -> dict[str, int]:
    columns = {}
    labels = [("STT", "STT"), ("Tên hàng", "THHDVu"), ("Đơn vị", "DVTinh"),
              ("Số lượng", "SLuong"), ("Đơn giá", "DGia"), ("Thành tiền", "ThTien"),
              ("Thuế suất", "TSuat"), ("Tiền thuế", "TThue"),
              ("Tỷ lệ chiết khấu", "TLCKhau"), ("Tiền chiết khấu", "STCKhau")]
    for index, cell in enumerate(row):
        for label, key in labels:
            if fold_accents(compact(cell)).casefold().startswith(fold_accents(label).casefold()):
                columns[key] = index
        english = {"STT": r"\bstt\b|\(no\.?\)", "THHDVu": r"\bdescription\b", "DVTinh": r"\(unit\)",
                   "SLuong": r"\bquantity\b", "DGia": r"\bunit price\b", "ThTien": r"\(amount\)"}
        for key, pattern in english.items():
            if re.search(pattern, cell, re.I):
                columns.setdefault(key, index)
    return columns if {"STT", "THHDVu", "SLuong", "DGia", "ThTien"} <= columns.keys() else {}


def apply_tables(document: dict, tables: list[dict], warnings: list[str]) -> None:
    content = document["NDHDon"]
    items, totals = content["DSHHDVu"], content["TToan"]
    for table in tables:
        columns = {}
        for index, raw in enumerate(table["rows"]):
            row = [compact(value) for value in raw]
            header = header_columns(row)
            if header:
                columns = header
                continue
            nonempty = [v for v in row if v]
            if not nonempty:
                continue
            # Totals may use merged cells and an entirely different column grid.
            first = nonempty[0].casefold()
            numeric = [v for v in nonempty[1:] if decimal_value(v) is not None]
            if first.startswith("tổng cộng") and len(numeric) == 3:
                for key, value in zip(("TgTCThue", "TgTThue", "TgTTTBSo"), numeric):
                    totals[key] = value
                columns = {}
                continue
            if first.startswith(("cộng tiền hàng", "tổng tiền chưa thuế")) and len(numeric) == 1:
                totals["TgTCThue"] = numeric[0]
                columns = {}
            if first.startswith(("tổng cộng tiền thanh toán", "tổng tiền thanh toán")) and len(numeric) == 1:
                totals["TgTTTBSo"] = numeric[0]
                columns = {}
            if any(v.casefold().startswith("tiền thuế gtgt") for v in nonempty) and len(numeric) == 1:
                totals["TgTThue"] = numeric[0]
                columns = {}
            if first.startswith("thuế suất"):
                rate = re.search(r"(\d+(?:,\d+)?)[ \t]*%", nonempty[0])
                if rate and len(numeric) == 3:
                    entry = {"TSuat": rate.group(1) + "%", "ThTien": numeric[0], "TThue": numeric[1]}
                    if entry not in totals["THTTLTSuat"]:
                        totals["THTTLTSuat"].append(entry)
            if not columns:
                continue
            values = {key: row[col] if col < len(row) else "" for key, col in columns.items()}
            description = values["THHDVu"]
            if not description or re.fullmatch(r"\(?\d+\)?", description):
                continue
            is_item = bool(re.fullmatch(r"\d+", values["STT"]))
            is_note = not values["STT"] and all(not values[key] for key in ("SLuong", "DGia", "ThTien"))
            if not is_item and not is_note:
                if any(values[key] for key in ("SLuong", "DGia", "ThTien")):
                    warnings.append(f"Trang {table['page']}: có dòng bảng chưa xác định được STT; cần đối chiếu file gốc.")
                else:
                    continue
            item = deepcopy(ITEM_FIELDS)
            item.update(values)
            item["TChat"] = "1" if is_item else ("4" if is_note else "")
            # Joining a wrapped contract identifier after '/' must not add a space.
            item["THHDVu"] = compact(re.sub(r"/[ \t]*\n[ \t]*(?=\w)", "/", raw[columns["THHDVu"]] or ""))
            source = {"page": table["page"], "method": table.get("method", "PDF table")}
            if "confidence" in table:
                source["confidence"] = {key: table["confidence"][index][col] for key, col in columns.items()}
                uncertain = [key for key in ("SLuong", "DGia", "ThTien", "TThue")
                             if values.get(key) and source["confidence"].get(key, 100) < 70]
                if uncertain:
                    warnings.append(f"Trang {table['page']}, dòng {values['STT'] or index}: OCR chưa chắc chắn ở {', '.join(uncertain)}.")
            if index < len(table.get("bboxes", [])):
                source["bbox"] = table["bboxes"][index]
            item["TTKhac"].append({"TTruong": "Nguồn trích xuất", "KDLieu": "string",
                                   "DLieu": f"Trang {source['page']} ({source['method']})"})
            # Structured evidence is retained in DocumentJson without changing DB schema.
            item["ExtractionSource"] = source
            items.append(item)


def validate_document(document: dict) -> list[str]:
    warnings = []
    content = document["NDHDon"]
    items = [item for item in content["DSHHDVu"] if item.get("TChat") == "1"]
    amounts, taxes, seen = [], [], set()
    for item in items:
        line = item.get("STT") or "?"
        if line in seen:
            warnings.append(f"STT {line} xuất hiện nhiều lần; cần kiểm tra bảng qua các trang.")
        seen.add(line)
        quantity, price, amount = (decimal_value(item.get(k, "")) for k in ("SLuong", "DGia", "ThTien"))
        if amount is not None:
            amounts.append(amount)
        if any(v is None for v in (quantity, price, amount)):
            warnings.append(f"Dòng {line}: thiếu hoặc chưa đọc rõ số lượng, đơn giá, thành tiền.")
        else:
            discount = decimal_value(item.get("STCKhau", ""))
            if not item.get("TLCKhau") and (not item.get("STCKhau") or discount is not None):
                if abs(quantity * price - (discount or Decimal(0)) - amount) > Decimal(1):
                    warnings.append(f"Dòng {line}: số lượng × đơn giá không khớp thành tiền (sau chiết khấu nếu có).")
        tax = decimal_value(item.get("TThue", ""))
        if tax is not None:
            taxes.append(tax)
    totals = content["TToan"]
    numeric_ids = [int(item["STT"]) for item in items if str(item.get("STT", "")).isdigit()]
    if numeric_ids and numeric_ids != list(range(1, len(numeric_ids) + 1)):
        warnings.append("STT dòng hàng không liên tục từ 1; có thể thiếu dòng hoặc hóa đơn dùng cách đánh số riêng.")
    subtotal, tax_total, total = (decimal_value(totals.get(k, "")) for k in ("TgTCThue", "TgTThue", "TgTTTBSo"))
    if items and len(amounts) == len(items) and subtotal is not None and abs(sum(amounts) - subtotal) > Decimal(1):
        warnings.append("Tổng thành tiền các dòng hàng không khớp tổng tiền trước thuế.")
    if items and len(taxes) == len(items) and tax_total is not None and abs(sum(taxes) - tax_total) > Decimal(1):
        warnings.append("Tổng tiền thuế các dòng hàng không khớp tổng thuế.")
    if all(v is not None for v in (subtotal, tax_total, total)) and abs(subtotal + tax_total - total) > Decimal(1):
        warnings.append("Tiền trước thuế + thuế không khớp tổng thanh toán; kiểm tra chiết khấu/phụ phí nếu có.")
    if content["DSHHDVu"] and total is None:
        warnings.append("Chưa đọc được tổng thanh toán; cần đối chiếu file gốc.")
    return warnings
