from __future__ import annotations

import base64
import json
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator

import pyodbc

from .schema import core_fields
from .db_common import DatabaseUnavailable


SCHEMA_STATEMENTS = [
    """
    IF OBJECT_ID(N'dbo.HoaDon', N'U') IS NULL
    BEGIN
      CREATE TABLE dbo.HoaDon (
        MaHoaDon UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
        TenFileNguon NVARCHAR(260) NOT NULL,
        LoaiFileNguon NVARCHAR(100) NULL,
        DaDungOCR BIT NOT NULL CONSTRAINT DF_HoaDon_DaDungOCR DEFAULT 0,
        VanBanOCR NVARCHAR(MAX) NULL,
        SHDon NVARCHAR(100) NULL,
        KHHDon NVARCHAR(100) NULL,
        KHMSHDon NVARCHAR(100) NULL,
        NLap DATE NULL,
        DVTTe NVARCHAR(20) NULL,
        HTTToan NVARCHAR(200) NULL,
        TenNguoiBan NVARCHAR(500) NULL,
        MSTNguoiBan NVARCHAR(50) NULL,
        TenNguoiMua NVARCHAR(500) NULL,
        MSTNguoiMua NVARCHAR(50) NULL,
        TgTCThue DECIMAL(19,4) NULL,
        TgTThue DECIMAL(19,4) NULL,
        TgTTTBSo DECIMAL(19,4) NULL,
        MCCQT NVARCHAR(100) NULL,
        TrangThai NVARCHAR(40) NOT NULL CONSTRAINT DF_HoaDon_TrangThai DEFAULT N'Đã lưu',
        DuLieuHoaDon NVARCHAR(MAX) NOT NULL,
        DuLieuFileNguon VARBINARY(MAX) NULL,
        NgayTao DATETIME2 NOT NULL CONSTRAINT DF_HoaDon_NgayTao DEFAULT SYSUTCDATETIME(),
        NgayCapNhat DATETIME2 NOT NULL CONSTRAINT DF_HoaDon_NgayCapNhat DEFAULT SYSUTCDATETIME()
      );
      CREATE INDEX IX_HoaDon_SHDon ON dbo.HoaDon(SHDon);
      CREATE INDEX IX_HoaDon_MSTNguoiBan ON dbo.HoaDon(MSTNguoiBan);
      CREATE INDEX IX_HoaDon_MSTNguoiMua ON dbo.HoaDon(MSTNguoiMua);
      CREATE INDEX IX_HoaDon_NLap ON dbo.HoaDon(NLap);
    END
    """,
    """
    IF OBJECT_ID(N'dbo.ChiTietHoaDon', N'U') IS NULL
    BEGIN
      CREATE TABLE dbo.ChiTietHoaDon (
        MaDong BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        MaHoaDon UNIQUEIDENTIFIER NOT NULL,
        STT INT NULL,
        MHHDVu NVARCHAR(100) NULL,
        THHDVu NVARCHAR(MAX) NULL,
        DVTinh NVARCHAR(100) NULL,
        SLuong DECIMAL(19,4) NULL,
        DGia DECIMAL(19,4) NULL,
        TLCKhau DECIMAL(9,4) NULL,
        STCKhau DECIMAL(19,4) NULL,
        ThTien DECIMAL(19,4) NULL,
        TSuat NVARCHAR(30) NULL,
        TThue DECIMAL(19,4) NULL,
        DuLieuDong NVARCHAR(MAX) NOT NULL,
        CONSTRAINT FK_ChiTietHoaDon_HoaDon FOREIGN KEY (MaHoaDon) REFERENCES dbo.HoaDon(MaHoaDon) ON DELETE CASCADE
      );
      CREATE INDEX IX_ChiTietHoaDon_MaHoaDon ON dbo.ChiTietHoaDon(MaHoaDon);
    END
    """,
    """
    IF OBJECT_ID(N'dbo.TruongMoRongHoaDon', N'U') IS NULL
    BEGIN
      CREATE TABLE dbo.TruongMoRongHoaDon (
        MaTruong BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        MaHoaDon UNIQUEIDENTIFIER NOT NULL,
        DuongDanNhom NVARCHAR(500) NOT NULL,
        TTruong NVARCHAR(500) NULL,
        KDLieu NVARCHAR(100) NULL,
        DLieu NVARCHAR(MAX) NULL,
        CONSTRAINT FK_TruongMoRongHoaDon_HoaDon FOREIGN KEY (MaHoaDon) REFERENCES dbo.HoaDon(MaHoaDon) ON DELETE CASCADE
      );
      CREATE INDEX IX_TruongMoRongHoaDon_MaHoaDon ON dbo.TruongMoRongHoaDon(MaHoaDon);
    END
    """,
]


def _decimal(value: Any) -> Decimal | None:
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
    cleaned = re_sub_non_numeric(cleaned)
    try:
        return Decimal(cleaned) if cleaned else None
    except InvalidOperation:
        return None


def re_sub_non_numeric(value: str) -> str:
    import re
    return re.sub(r"[^0-9.\-]", "", value)


def _date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _integer(value: Any, fallback: int) -> int:
    try:
        return int(str(value).strip()) if value not in (None, "") else fallback
    except ValueError:
        return fallback


class InvoiceRepository:
    engine_name = "Microsoft SQL Server (pyodbc)"

    def __init__(self, connection_string: str | None):
        self.connection_string = connection_string

    @property
    def configured(self) -> bool:
        return bool(self.connection_string)

    @contextmanager
    def connect(self) -> Iterator[pyodbc.Connection]:
        if not self.connection_string:
            raise DatabaseUnavailable("Chưa cấu hình SQLSERVER_CONNECTION_STRING.")
        try:
            connection = pyodbc.connect(self.connection_string, timeout=8)
        except pyodbc.Error as exc:
            raise DatabaseUnavailable(f"Không thể kết nối SQL Server: {exc}") from exc
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            cursor = connection.cursor()
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
            connection.commit()

    def _sync_children(self, cursor: pyodbc.Cursor, invoice_id: str, document: dict[str, Any]) -> None:
        cursor.execute("DELETE FROM dbo.ChiTietHoaDon WHERE MaHoaDon = ?", invoice_id)
        cursor.execute("DELETE FROM dbo.TruongMoRongHoaDon WHERE MaHoaDon = ?", invoice_id)
        content = document.get("NDHDon", {})
        for index, item in enumerate(content.get("DSHHDVu", []), start=1):
            cursor.execute(
                """INSERT INTO dbo.ChiTietHoaDon
                (MaHoaDon, STT, MHHDVu, THHDVu, DVTinh, SLuong, DGia,
                 TLCKhau, STCKhau, ThTien, TSuat, TThue, DuLieuDong)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                invoice_id,
                _integer(item.get("STT"), index),
                item.get("MHHDVu"), item.get("THHDVu"), item.get("DVTinh"),
                _decimal(item.get("SLuong")), _decimal(item.get("DGia")),
                _decimal(item.get("TLCKhau")), _decimal(item.get("STCKhau")),
                _decimal(item.get("ThTien")), item.get("TSuat"), _decimal(item.get("TThue")),
                json.dumps(item, ensure_ascii=False),
            )

        def collect(value: Any, path: str = "") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    next_path = f"{path}.{key}" if path else key
                    if key == "TTKhac" and isinstance(child, list):
                        for extra in child:
                            if isinstance(extra, dict):
                                cursor.execute(
                                    """INSERT INTO dbo.TruongMoRongHoaDon
                                    (MaHoaDon, DuongDanNhom, TTruong, KDLieu, DLieu)
                                    VALUES (?, ?, ?, ?, ?)""",
                                    invoice_id, path or "HDon", extra.get("TTruong"),
                                    extra.get("KDLieu"), str(extra.get("DLieu") or ""),
                                )
                    collect(child, next_path)
            elif isinstance(value, list):
                for idx, child in enumerate(value):
                    collect(child, f"{path}[{idx}]")

        collect(document)

    def create(self, draft: dict[str, Any]) -> str:
        invoice_id = str(uuid.uuid4())
        document = draft.get("document") or {}
        core = core_fields(document)
        source_data = base64.b64decode(draft.get("source_base64") or "", validate=True)
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO dbo.HoaDon
                (MaHoaDon, TenFileNguon, LoaiFileNguon, DaDungOCR, VanBanOCR, SHDon, KHHDon,
                 KHMSHDon, NLap, DVTTe, HTTToan, TenNguoiBan, MSTNguoiBan,
                 TenNguoiMua, MSTNguoiMua, TgTCThue, TgTThue, TgTTTBSo, MCCQT,
                 DuLieuHoaDon, DuLieuFileNguon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                invoice_id, draft.get("filename") or "invoice", draft.get("content_type"),
                bool(draft.get("ocr_enabled")), draft.get("extracted_text"),
                core["invoice_number"], core["series"], core["form_number"],
                _date(core["issue_date"]), core["currency"], core["payment_method"],
                core["seller_name"], core["seller_tax_code"], core["buyer_name"],
                core["buyer_tax_code"], _decimal(core["subtotal"]), _decimal(core["tax_total"]),
                _decimal(core["grand_total"]), core["tax_authority_code"],
                json.dumps(document, ensure_ascii=False), source_data,
            )
            self._sync_children(cursor, invoice_id, document)
            connection.commit()
        return invoice_id

    def update(self, invoice_id: str, document: dict[str, Any]) -> None:
        core = core_fields(document)
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """UPDATE dbo.HoaDon SET SHDon=?, KHHDon=?, KHMSHDon=?, NLap=?,
                DVTTe=?, HTTToan=?, TenNguoiBan=?, MSTNguoiBan=?, TenNguoiMua=?, MSTNguoiMua=?,
                TgTCThue=?, TgTThue=?, TgTTTBSo=?, MCCQT=?, DuLieuHoaDon=?,
                NgayCapNhat=SYSUTCDATETIME() WHERE MaHoaDon=?""",
                core["invoice_number"], core["series"], core["form_number"], _date(core["issue_date"]),
                core["currency"], core["payment_method"], core["seller_name"], core["seller_tax_code"],
                core["buyer_name"], core["buyer_tax_code"], _decimal(core["subtotal"]),
                _decimal(core["tax_total"]), _decimal(core["grand_total"]), core["tax_authority_code"],
                json.dumps(document, ensure_ascii=False), invoice_id,
            )
            if cursor.rowcount == 0:
                raise KeyError(invoice_id)
            self._sync_children(cursor, invoice_id, document)
            connection.commit()

    def list(self, query: str = "", page: int = 1, page_size: int = 25) -> dict[str, Any]:
        where = ""
        params: list[Any] = []
        if query:
            where = """WHERE SHDon LIKE ? OR TenNguoiBan LIKE ? OR MSTNguoiBan LIKE ?
              OR TenNguoiMua LIKE ? OR MSTNguoiMua LIKE ? OR MCCQT LIKE ? OR DuLieuHoaDon LIKE ?"""
            needle = f"%{query}%"
            params = [needle] * 7
        offset = max(0, page - 1) * page_size
        with self.connect() as connection:
            cursor = connection.cursor()
            total = cursor.execute(f"SELECT COUNT(*) FROM dbo.HoaDon {where}", *params).fetchval()
            rows = cursor.execute(
                f"""SELECT MaHoaDon AS Id, TenFileNguon AS SourceFilename,
                LoaiFileNguon AS SourceType, DaDungOCR AS OcrEnabled, SHDon AS InvoiceNumber,
                KHHDon AS Series, NLap AS IssueDate, DVTTe AS Currency,
                TenNguoiBan AS SellerName, MSTNguoiBan AS SellerTaxCode,
                TenNguoiMua AS BuyerName, MSTNguoiMua AS BuyerTaxCode,
                TgTTTBSo AS GrandTotal, TrangThai AS Status, NgayTao AS CreatedAt,
                NgayCapNhat AS UpdatedAt
                FROM dbo.HoaDon {where}
                ORDER BY NgayTao DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
                *params, offset, page_size,
            ).fetchall()
            columns = [description[0] for description in cursor.description]
        return {"items": [self._serialize(dict(zip(columns, row))) for row in rows], "total": total}

    def get(self, invoice_id: str, include_source: bool = True) -> dict[str, Any] | None:
        source_column = ", DuLieuFileNguon AS SourceData" if include_source else ""
        with self.connect() as connection:
            cursor = connection.cursor()
            row = cursor.execute(
                f"""SELECT MaHoaDon AS Id, TenFileNguon AS SourceFilename,
                LoaiFileNguon AS SourceType, DaDungOCR AS OcrEnabled, VanBanOCR AS OcrText,
                TrangThai AS Status, DuLieuHoaDon AS DocumentJson, NgayTao AS CreatedAt,
                NgayCapNhat AS UpdatedAt{source_column} FROM dbo.HoaDon WHERE MaHoaDon=?""",
                invoice_id,
            ).fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
        result = dict(zip(columns, row))
        result["document"] = json.loads(result.pop("DocumentJson"))
        if "SourceData" in result:
            result["source_base64"] = base64.b64encode(result.pop("SourceData") or b"").decode("ascii")
        return self._serialize(result)

    def delete(self, invoice_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM dbo.HoaDon WHERE MaHoaDon=?", invoice_id)
            deleted = cursor.rowcount > 0
            connection.commit()
        return deleted

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
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, uuid.UUID):
            return str(value)
        return value
