IF DB_ID(N'HoaDon') IS NULL
BEGIN
    CREATE DATABASE HoaDon;
END;
GO

USE HoaDon;
GO

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
END;
GO

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
        CONSTRAINT FK_ChiTietHoaDon_HoaDon FOREIGN KEY (MaHoaDon)
            REFERENCES dbo.HoaDon(MaHoaDon) ON DELETE CASCADE
    );
    CREATE INDEX IX_ChiTietHoaDon_MaHoaDon ON dbo.ChiTietHoaDon(MaHoaDon);
END;
GO

IF OBJECT_ID(N'dbo.TruongMoRongHoaDon', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.TruongMoRongHoaDon (
        MaTruong BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        MaHoaDon UNIQUEIDENTIFIER NOT NULL,
        DuongDanNhom NVARCHAR(500) NOT NULL,
        TTruong NVARCHAR(500) NULL,
        KDLieu NVARCHAR(100) NULL,
        DLieu NVARCHAR(MAX) NULL,
        CONSTRAINT FK_TruongMoRongHoaDon_HoaDon FOREIGN KEY (MaHoaDon)
            REFERENCES dbo.HoaDon(MaHoaDon) ON DELETE CASCADE
    );
    CREATE INDEX IX_TruongMoRongHoaDon_MaHoaDon ON dbo.TruongMoRongHoaDon(MaHoaDon);
END;
GO
