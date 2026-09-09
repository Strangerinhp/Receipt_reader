from __future__ import annotations

from copy import deepcopy
from typing import Any


GENERAL_FIELDS = {
    "PBan": "",
    "THDon": "",
    "KHMSHDon": "",
    "KHHDon": "",
    "SHDon": "",
    "NLap": "",
    "DVTTe": "",
    "TGia": "",
    "HTTToan": "",
    "MSTTCGP": "",
    "MSTDVNUNLHDon": "",
    "TDVNUNLHDon": "",
    "DCDVNUNLHDon": "",
    "TTKhac": [],
    "HDCTTChinh": "",
}

SELLER_FIELDS = {
    "Ten": "",
    "MST": "",
    "DChi": "",
    "SDThoai": "",
    "DCTDTu": "",
    "STKNHang": "",
    "TNHang": "",
    "Fax": "",
    "Website": "",
    "TTKhac": [],
}

BUYER_FIELDS = {
    "Ten": "",
    "MST": "",
    "DChi": "",
    "MKHang": "",
    "SDThoai": "",
    "DCTDTu": "",
    "HVTNMHang": "",
    "STKNHang": "",
    "TNHang": "",
    "TTKhac": [],
}

ITEM_FIELDS = {
    "TChat": "",
    "STT": "",
    "MHHDVu": "",
    "THHDVu": "",
    "DVTinh": "",
    "SLuong": "",
    "DGia": "",
    "TLCKhau": "",
    "STCKhau": "",
    "ThTien": "",
    "TSuat": "",
    "TThue": "",
    "TTKhac": [],
}

TOTAL_FIELDS = {
    "THTTLTSuat": [],
    "TgTCThue": "",
    "TgTThue": "",
    "DSLPhi": [],
    "TTCKTMai": "",
    "TgTTTBSo": "",
    "TgTTTBChu": "",
    "TTKhac": [],
}


def invoice_template() -> dict[str, Any]:
    """Canonical Vietnamese e-invoice shape used for every input type."""
    return {
        "TTChung": deepcopy(GENERAL_FIELDS),
        "NDHDon": {
            "NBan": deepcopy(SELLER_FIELDS),
            "NMua": deepcopy(BUYER_FIELDS),
            "DSHHDVu": [],
            "TToan": deepcopy(TOTAL_FIELDS),
            "TTKhac": [],
        },
        "MCCQT": "",
        "DSCKS": {},
    }


def deep_merge(template: Any, parsed: Any) -> Any:
    """Keep template fields while preserving every vendor-specific XML field."""
    if isinstance(template, dict) and isinstance(parsed, dict):
        result = deepcopy(template)
        for key, value in parsed.items():
            result[key] = deep_merge(result[key], value) if key in result else value
        return result
    if isinstance(template, list) and isinstance(parsed, list):
        return parsed
    return parsed if parsed is not None else deepcopy(template)


def normalize_invoice_document(parsed: dict[str, Any]) -> dict[str, Any]:
    data = parsed.get("HDon", parsed)
    if isinstance(data, dict) and "DLHDon" in data:
        data = {**data["DLHDon"], **{k: v for k, v in data.items() if k != "DLHDon"}}

    data = deepcopy(data) if isinstance(data, dict) else {}

    def normalize_extra_groups(value: Any) -> Any:
        if isinstance(value, dict):
            for key, child in list(value.items()):
                if key == "TTKhac" and isinstance(child, dict):
                    extra_items = child.get("TTin", [])
                    if isinstance(extra_items, dict):
                        extra_items = [extra_items]
                    value[key] = extra_items if isinstance(extra_items, list) else []
                else:
                    value[key] = normalize_extra_groups(child)
        elif isinstance(value, list):
            return [normalize_extra_groups(item) for item in value]
        return value

    data = normalize_extra_groups(data)
    content = data.setdefault("NDHDon", {})

    items = content.get("DSHHDVu", [])
    if isinstance(items, dict):
        items = items.get("HHDVu", [])
    if isinstance(items, dict):
        items = [items]
    content["DSHHDVu"] = items if isinstance(items, list) else []

    totals = content.get("TToan", {})
    if isinstance(totals, dict):
        rates = totals.get("THTTLTSuat", [])
        if isinstance(rates, dict):
            rates = rates.get("LTSuat", [])
        if isinstance(rates, dict):
            rates = [rates]
        totals["THTTLTSuat"] = rates if isinstance(rates, list) else []

        fees = totals.get("DSLPhi", [])
        if isinstance(fees, dict):
            fees = fees.get("LPhi", fees.get("Phi", []))
        if isinstance(fees, dict):
            fees = [fees]
        totals["DSLPhi"] = fees if isinstance(fees, list) else []

    return deep_merge(invoice_template(), data)


def core_fields(document: dict[str, Any]) -> dict[str, Any]:
    general = document.get("TTChung", {})
    content = document.get("NDHDon", {})
    seller = content.get("NBan", {})
    buyer = content.get("NMua", {})
    totals = content.get("TToan", {})
    return {
        "invoice_number": general.get("SHDon") or "",
        "series": general.get("KHHDon") or "",
        "form_number": general.get("KHMSHDon") or "",
        "issue_date": general.get("NLap") or None,
        "currency": general.get("DVTTe") or "",
        "payment_method": general.get("HTTToan") or "",
        "seller_name": seller.get("Ten") or "",
        "seller_tax_code": seller.get("MST") or "",
        "buyer_name": buyer.get("Ten") or "",
        "buyer_tax_code": buyer.get("MST") or "",
        "subtotal": totals.get("TgTCThue") or None,
        "tax_total": totals.get("TgTThue") or None,
        "grand_total": totals.get("TgTTTBSo") or None,
        "tax_authority_code": document.get("MCCQT") or "",
    }
