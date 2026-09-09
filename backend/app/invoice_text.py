"""Label extraction for Vietnamese invoices. Blank fields never consume a new line."""
from __future__ import annotations

from datetime import date
import re
import unicodedata

from .schema import invoice_template


def compact(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def fold_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value.replace("đ", "d").replace("Đ", "D"))
                   if not unicodedata.combining(c))


# Match the complete bilingual label, including its colon, before taking a value.
LABELS = {
    "number": r"Số(?: hóa đơn| HĐ)?|Invoice (?:No\.?|number)|\(No[.,]?\)",
    "series": r"Ký hiệu|Serial",
    "date": r"Ngày lập|Ngày hóa đơn|Invoice date",
    "payment": r"Hình thức thanh toán|Payment method",
    "currency": r"Đơn vị tiền tệ|Currency",
    "seller": r"Đơn vị bán hàng|Tên người bán|\(Seller\)",
    "buyer": r"Tên đơn vị|Đơn vị mua hàng|\(Company's name\)",
    "person": r"Họ(?: và)? tên người mua(?: hàng)?|Họ và tên người mua|\(Customer's name\)|\(Buyer's fullname\)",
    "tax": r"Mã số thuế|Tax code|\(Tax code\)",
    "address": r"Địa chỉ|Address",
    "phone": r"Điện thoại|Tel",
    "email": r"Email",
    "account": r"Số tài khoản|Account No\.?",
    "bank": r"Ngân hàng|Bank",
    "fax": r"Fax",
    "website": r"Website",
    "subtotal": r"Cộng tiền hàng|Tổng tiền chưa thuế|Subtotal|\(Total amount\)",
    "tax_total": r"Tiền thuế GTGT|Tổng tiền thuế|VAT amount|\(VAT amount\)",
    "total": r"Tổng cộng tiền thanh toán|Tổng tiền thanh toán|Tổng cộng|Total payment|\(Total payment\)",
    "words": r"Số tiền viết bằng chữ|Amount in words",
    "authority": r"Mã của cơ quan thuế|Mã cơ quan thuế|Mã CQT",
    "rate": r"Thuế suất GTGT|Thuế suất|VAT rate",
    "other": r"MSĐVCQHVNS|Mã đơn vị quan hệ ngân sách|Căn cước công dân|Số hộ chiếu|Ghi chú|Mã tra cứu|Mã số bí mật",
}
LABEL_RE = re.compile(
    r"(?<!\w)(?:" + "|".join(f"(?P<{key}>{pattern})" for key, pattern in LABELS.items())
    + r")[ \t]*(?:\([^\r\n)]*\)[ \t]*)?[:：][ \t]*", re.I
)
FOLDED_LABEL_RE = re.compile(fold_accents(LABEL_RE.pattern), re.I)


def label_values(text: str, multiline: bool = False) -> list[tuple[str, str]]:
    values = []
    for line in unicodedata.normalize("NFC", text).splitlines():
        line = compact(line)
        matches = list(FOLDED_LABEL_RE.finditer(fold_accents(line)))
        if multiline and line and not matches and values and values[-1][0] in {"seller", "buyer", "address", "bank"}:
            if not re.search(r":|HÓA ĐƠN|Ngày |Người |Ghi chú|STT", line, re.I):
                label, previous = values[-1]
                values[-1] = (label, compact(previous + " " + line))
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
            values.append((match.lastgroup, compact(line[match.end():end])))
    return values


def value_after_label(text: str, labels: list[str]) -> str:
    """Compatibility helper for callers with custom regex labels."""
    for line in text.splitlines():
        for label in labels:
            match = re.search(rf"(?:{label})[ \t]*(?:\([^\r\n)]*\))?[ \t]*[:：][ \t]*", line, re.I)
            if match:
                rest = line[match.end():]
                following = LABEL_RE.search(rest)
                return compact(rest[:following.start()] if following else rest)
    return ""


def document_from_text(text: str) -> dict:
    document = invoice_template()
    general, content = document["TTChung"], document["NDHDon"]
    text = unicodedata.normalize("NFC", text)
    # Repeated party details on continuation pages must not become another party.
    first_page = text.split("\f", 1)[0]
    header = re.split(r"\bSTT\b", first_page, maxsplit=1, flags=re.I)[0]
    buyer_start = re.search(r"Ho(?: va)? ten nguoi mua(?: hang)?|Ten don vi|Don vi mua hang", fold_accents(header), re.I)
    seller_text = header[:buyer_start.start()] if buyer_start else header
    buyer_text = header[buyer_start.start():] if buyer_start else ""
    field_map = {"tax": "MST", "address": "DChi", "phone": "SDThoai", "email": "DCTDTu",
                 "account": "STKNHang", "bank": "TNHang", "fax": "Fax", "website": "Website",
                 "person": "HVTNMHang", "seller": "Ten", "buyer": "Ten"}
    for key, region in (("NBan", seller_text), ("NMua", buyer_text)):
        party = content[key]
        seen = set()
        for label, value in label_values(region, multiline=True):
            field = field_map.get(label)
            if field in party and field not in seen:
                party[field] = value.strip(" |_")
                if field == "MST":
                    match = re.match(r"\d{10}(?:-\d{3})?\b", value)
                    party[field] = match.group() if match else ""
                if field == "STKNHang":
                    bank = re.search(r"\bNgan hang\b[ :]*", fold_accents(value), re.I)
                    if bank:
                        party["STKNHang"] = value[:bank.start()].strip()
                        party["TNHang"] = value[bank.end():].strip(" |_")
                seen.add(field)
        # Some providers print an unlabelled seller name immediately before MST.
        if key == "NBan" and not party["Ten"]:
            lines = [compact(line) for line in region.splitlines() if compact(line)]
            for i, line in enumerate(lines):
                if re.match(r"Mã số thuế", line, re.I) and i:
                    previous = lines[i - 1]
                    if re.match(r"CÔNG TY|DOANH NGHIỆP|HỘ KINH DOANH|CHI NHÁNH", previous, re.I):
                        party["Ten"] = previous
                    break
    mapping = {"number": "SHDon", "series": "KHHDon", "payment": "HTTToan", "currency": "DVTTe", "date": "NLap"}
    for label, value in label_values(header):
        field = mapping.get(label)
        if field and not general[field]:
            general[field] = value
    display_date = re.search(
        r"Ngay\s*(?:\(date\))?\s*(\d{1,2})\s*thang\s*(?:\(month\))?\s*(\d{1,2})\s*nam\s*(?:\(year\))?\s*(\d{4})", fold_accents(header), re.I)
    slash_date = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", general["NLap"])
    if display_date or slash_date:
        day, month, year = (display_date or slash_date).groups()
        try:
            general["NLap"] = date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            general["NLap"] = ""
    if not general["DVTTe"] and re.search(r"HÓA ĐƠN|Mã số thuế", header, re.I):
        general["DVTTe"] = "VND"
    totals = content["TToan"]
    total_map = {"subtotal": "TgTCThue", "tax_total": "TgTThue", "total": "TgTTTBSo"}
    for label, value in label_values(text):
        if label in total_map:
            # A summary row containing three amounts needs table column mapping.
            if re.fullmatch(r"[-+]?\d[\d.,]*", value):
                totals[total_map[label]] = value
        elif label == "words" and not totals["TgTTTBChu"]:
            totals["TgTTTBChu"] = value
        elif label == "authority" and not document["MCCQT"]:
            match = re.match(r"[A-Za-z0-9]+", value)
            document["MCCQT"] = match.group() if match else ""
    return document
