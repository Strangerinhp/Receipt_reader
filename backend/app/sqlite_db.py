from __future__ import annotations

import base64
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

from .db_common import DatabaseUnavailable
from .schema import core_fields


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS Invoices (
    Id TEXT NOT NULL PRIMARY KEY,
    SourceFilename TEXT NOT NULL,
    SourceType TEXT,
    OcrEnabled INTEGER NOT NULL DEFAULT 0,
    OcrText TEXT,
    InvoiceNumber TEXT,
    Series TEXT,
    FormNumber TEXT,
    IssueDate TEXT,
    Currency TEXT,
    PaymentMethod TEXT,
    SellerName TEXT,
    SellerTaxCode TEXT,
    BuyerName TEXT,
    BuyerTaxCode TEXT,
    Subtotal TEXT,
    TaxTotal TEXT,
    GrandTotal TEXT,
    TaxAuthorityCode TEXT,
    Status TEXT NOT NULL DEFAULT 'Đã lưu',
    DocumentJson TEXT NOT NULL,
    SourceData BLOB,
    CreatedAt TEXT NOT NULL,
    UpdatedAt TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS IX_Invoices_InvoiceNumber ON Invoices(InvoiceNumber);
CREATE INDEX IF NOT EXISTS IX_Invoices_SellerTaxCode ON Invoices(SellerTaxCode);
CREATE INDEX IF NOT EXISTS IX_Invoices_BuyerTaxCode ON Invoices(BuyerTaxCode);
CREATE INDEX IF NOT EXISTS IX_Invoices_IssueDate ON Invoices(IssueDate);

CREATE TABLE IF NOT EXISTS InvoiceItems (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    InvoiceId TEXT NOT NULL,
    LineNumber INTEGER,
    ItemCode TEXT,
    Description TEXT,
    Unit TEXT,
    Quantity TEXT,
    UnitPrice TEXT,
    DiscountRate TEXT,
    DiscountAmount TEXT,
    Amount TEXT,
    TaxRate TEXT,
    TaxAmount TEXT,
    ItemJson TEXT NOT NULL,
    FOREIGN KEY (InvoiceId) REFERENCES Invoices(Id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS IX_InvoiceItems_InvoiceId ON InvoiceItems(InvoiceId);

CREATE TABLE IF NOT EXISTS InvoiceExtraFields (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    InvoiceId TEXT NOT NULL,
    GroupPath TEXT NOT NULL,
    FieldName TEXT,
    DataType TEXT,
    FieldValue TEXT,
    FOREIGN KEY (InvoiceId) REFERENCES Invoices(Id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS IX_InvoiceExtraFields_InvoiceId ON InvoiceExtraFields(InvoiceId);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decimal_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    cleaned = str(value).replace(" ", "").replace("₫", "").replace("VND", "")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") > 1 or (cleaned.count(",") == 1 and len(cleaned.rsplit(",", 1)[1]) == 3):
        cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(".") > 1 or (cleaned.count(".") == 1 and len(cleaned.rsplit(".", 1)[1]) == 3):
        cleaned = cleaned.replace(".", "")
    import re
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    try:
        return format(Decimal(cleaned), "f") if cleaned else None
    except InvalidOperation:
        return None


def _date_text(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _integer(value: Any, fallback: int) -> int:
    try:
        return int(str(value).strip()) if value not in (None, "") else fallback
    except ValueError:
        return fallback


class SQLiteInvoiceRepository:
    engine_name = "SQLite"

    def __init__(self, database_path: str):
        self.database_path = str(Path(database_path).expanduser().resolve())

    @property
    def configured(self) -> bool:
        return bool(self.database_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        try:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path, timeout=15)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 15000")
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(f"Không thể mở SQLite database: {exc}") from exc
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        try:
            with self.connect() as connection:
                connection.executescript(SQLITE_SCHEMA)
                connection.execute("PRAGMA journal_mode = WAL")
                connection.commit()
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(f"Không thể khởi tạo SQLite database: {exc}") from exc

    def _sync_children(self, connection: sqlite3.Connection, invoice_id: str, document: dict[str, Any]) -> None:
        connection.execute("DELETE FROM InvoiceItems WHERE InvoiceId = ?", (invoice_id,))
        connection.execute("DELETE FROM InvoiceExtraFields WHERE InvoiceId = ?", (invoice_id,))
        content = document.get("NDHDon", {})
        for index, item in enumerate(content.get("DSHHDVu", []), start=1):
            connection.execute(
                """INSERT INTO InvoiceItems
                (InvoiceId, LineNumber, ItemCode, Description, Unit, Quantity, UnitPrice,
                 DiscountRate, DiscountAmount, Amount, TaxRate, TaxAmount, ItemJson)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    invoice_id, _integer(item.get("STT"), index), item.get("MHHDVu"),
                    item.get("THHDVu"), item.get("DVTinh"), _decimal_text(item.get("SLuong")),
                    _decimal_text(item.get("DGia")), _decimal_text(item.get("TLCKhau")),
                    _decimal_text(item.get("STCKhau")), _decimal_text(item.get("ThTien")),
                    item.get("TSuat"), _decimal_text(item.get("TThue")),
                    json.dumps(item, ensure_ascii=False),
                ),
            )

        def collect(value: Any, path: str = "") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    next_path = f"{path}.{key}" if path else key
                    if key == "TTKhac" and isinstance(child, list):
                        for extra in child:
                            if isinstance(extra, dict):
                                connection.execute(
                                    """INSERT INTO InvoiceExtraFields
                                    (InvoiceId, GroupPath, FieldName, DataType, FieldValue)
                                    VALUES (?, ?, ?, ?, ?)""",
                                    (
                                        invoice_id, path or "HDon", extra.get("TTruong"),
                                        extra.get("KDLieu"), str(extra.get("DLieu") or ""),
                                    ),
                                )
                    collect(child, next_path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    collect(child, f"{path}[{index}]")

        collect(document)

    def create(self, draft: dict[str, Any]) -> str:
        invoice_id = str(uuid.uuid4())
        document = draft.get("document") or {}
        core = core_fields(document)
        source_data = base64.b64decode(draft.get("source_base64") or "", validate=True)
        timestamp = _now()
        try:
            with self.connect() as connection:
                connection.execute(
                    """INSERT INTO Invoices
                    (Id, SourceFilename, SourceType, OcrEnabled, OcrText, InvoiceNumber, Series,
                     FormNumber, IssueDate, Currency, PaymentMethod, SellerName, SellerTaxCode,
                     BuyerName, BuyerTaxCode, Subtotal, TaxTotal, GrandTotal, TaxAuthorityCode,
                     DocumentJson, SourceData, CreatedAt, UpdatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        invoice_id, draft.get("filename") or "invoice", draft.get("content_type"),
                        int(bool(draft.get("ocr_enabled"))), draft.get("extracted_text"),
                        core["invoice_number"], core["series"], core["form_number"],
                        _date_text(core["issue_date"]), core["currency"], core["payment_method"],
                        core["seller_name"], core["seller_tax_code"], core["buyer_name"],
                        core["buyer_tax_code"], _decimal_text(core["subtotal"]),
                        _decimal_text(core["tax_total"]), _decimal_text(core["grand_total"]),
                        core["tax_authority_code"], json.dumps(document, ensure_ascii=False),
                        source_data, timestamp, timestamp,
                    ),
                )
                self._sync_children(connection, invoice_id, document)
                connection.commit()
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(f"Không thể lưu hóa đơn vào SQLite: {exc}") from exc
        return invoice_id

    def update(self, invoice_id: str, document: dict[str, Any]) -> None:
        core = core_fields(document)
        try:
            with self.connect() as connection:
                cursor = connection.execute(
                    """UPDATE Invoices SET InvoiceNumber=?, Series=?, FormNumber=?, IssueDate=?,
                    Currency=?, PaymentMethod=?, SellerName=?, SellerTaxCode=?, BuyerName=?, BuyerTaxCode=?,
                    Subtotal=?, TaxTotal=?, GrandTotal=?, TaxAuthorityCode=?, DocumentJson=?, UpdatedAt=?
                    WHERE Id=?""",
                    (
                        core["invoice_number"], core["series"], core["form_number"],
                        _date_text(core["issue_date"]), core["currency"], core["payment_method"],
                        core["seller_name"], core["seller_tax_code"], core["buyer_name"],
                        core["buyer_tax_code"], _decimal_text(core["subtotal"]),
                        _decimal_text(core["tax_total"]), _decimal_text(core["grand_total"]),
                        core["tax_authority_code"], json.dumps(document, ensure_ascii=False),
                        _now(), invoice_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise KeyError(invoice_id)
                self._sync_children(connection, invoice_id, document)
                connection.commit()
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(f"Không thể cập nhật SQLite database: {exc}") from exc

    def list(self, query: str = "", page: int = 1, page_size: int = 25) -> dict[str, Any]:
        where = ""
        params: list[Any] = []
        if query:
            where = """WHERE InvoiceNumber LIKE ? OR SellerName LIKE ? OR SellerTaxCode LIKE ?
              OR BuyerName LIKE ? OR BuyerTaxCode LIKE ? OR TaxAuthorityCode LIKE ? OR DocumentJson LIKE ?"""
            params = [f"%{query}%"] * 7
        offset = max(0, page - 1) * page_size
        try:
            with self.connect() as connection:
                total = connection.execute(f"SELECT COUNT(*) FROM Invoices {where}", params).fetchone()[0]
                rows = connection.execute(
                    f"""SELECT Id, SourceFilename, SourceType, OcrEnabled, InvoiceNumber, Series,
                    IssueDate, Currency, SellerName, SellerTaxCode, BuyerName, BuyerTaxCode,
                    GrandTotal, Status, CreatedAt, UpdatedAt FROM Invoices {where}
                    ORDER BY CreatedAt DESC LIMIT ? OFFSET ?""",
                    [*params, page_size, offset],
                ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(f"Không thể đọc SQLite database: {exc}") from exc
        return {"items": [self._serialize(dict(row)) for row in rows], "total": total}

    def get(self, invoice_id: str, include_source: bool = True) -> dict[str, Any] | None:
        source_column = ", SourceData" if include_source else ""
        try:
            with self.connect() as connection:
                row = connection.execute(
                    f"""SELECT Id, SourceFilename, SourceType, OcrEnabled, OcrText, Status,
                    DocumentJson, CreatedAt, UpdatedAt{source_column} FROM Invoices WHERE Id=?""",
                    (invoice_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(f"Không thể đọc SQLite database: {exc}") from exc
        if not row:
            return None
        result = dict(row)
        result["document"] = json.loads(result.pop("DocumentJson"))
        if "SourceData" in result:
            result["source_base64"] = base64.b64encode(result.pop("SourceData") or b"").decode("ascii")
        return self._serialize(result)

    def delete(self, invoice_id: str) -> bool:
        try:
            with self.connect() as connection:
                cursor = connection.execute("DELETE FROM Invoices WHERE Id=?", (invoice_id,))
                connection.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(f"Không thể xóa hóa đơn khỏi SQLite: {exc}") from exc

    @classmethod
    def _serialize(cls, value: Any, *, transform_keys: bool = True) -> Any:
        if isinstance(value, dict):
            return {
                (key[0].lower() + key[1:] if key and transform_keys else key): cls._serialize(
                    item, transform_keys=False
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._serialize(item, transform_keys=False) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value
