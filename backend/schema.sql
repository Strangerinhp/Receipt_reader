IF DB_ID(N'InvoiceOCR') IS NULL
BEGIN
    CREATE DATABASE InvoiceOCR;
END;
GO

USE InvoiceOCR;
GO

IF OBJECT_ID(N'dbo.Invoices', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Invoices (
        Id UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
        SourceFilename NVARCHAR(260) NOT NULL,
        SourceType NVARCHAR(100) NULL,
        OcrEnabled BIT NOT NULL CONSTRAINT DF_Invoices_OcrEnabled DEFAULT 0,
        OcrText NVARCHAR(MAX) NULL,
        InvoiceNumber NVARCHAR(100) NULL,
        Series NVARCHAR(100) NULL,
        FormNumber NVARCHAR(100) NULL,
        IssueDate DATE NULL,
        Currency NVARCHAR(20) NULL,
        PaymentMethod NVARCHAR(200) NULL,
        SellerName NVARCHAR(500) NULL,
        SellerTaxCode NVARCHAR(50) NULL,
        BuyerName NVARCHAR(500) NULL,
        BuyerTaxCode NVARCHAR(50) NULL,
        Subtotal DECIMAL(19,4) NULL,
        TaxTotal DECIMAL(19,4) NULL,
        GrandTotal DECIMAL(19,4) NULL,
        TaxAuthorityCode NVARCHAR(100) NULL,
        Status NVARCHAR(40) NOT NULL CONSTRAINT DF_Invoices_Status DEFAULT N'Đã lưu',
        DocumentJson NVARCHAR(MAX) NOT NULL,
        SourceData VARBINARY(MAX) NULL,
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_Invoices_CreatedAt DEFAULT SYSUTCDATETIME(),
        UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_Invoices_UpdatedAt DEFAULT SYSUTCDATETIME()
    );
    CREATE INDEX IX_Invoices_InvoiceNumber ON dbo.Invoices(InvoiceNumber);
    CREATE INDEX IX_Invoices_SellerTaxCode ON dbo.Invoices(SellerTaxCode);
    CREATE INDEX IX_Invoices_BuyerTaxCode ON dbo.Invoices(BuyerTaxCode);
    CREATE INDEX IX_Invoices_IssueDate ON dbo.Invoices(IssueDate);
END;
GO

IF OBJECT_ID(N'dbo.InvoiceItems', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.InvoiceItems (
        Id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        InvoiceId UNIQUEIDENTIFIER NOT NULL,
        LineNumber INT NULL,
        ItemCode NVARCHAR(100) NULL,
        Description NVARCHAR(MAX) NULL,
        Unit NVARCHAR(100) NULL,
        Quantity DECIMAL(19,4) NULL,
        UnitPrice DECIMAL(19,4) NULL,
        DiscountRate DECIMAL(9,4) NULL,
        DiscountAmount DECIMAL(19,4) NULL,
        Amount DECIMAL(19,4) NULL,
        TaxRate NVARCHAR(30) NULL,
        TaxAmount DECIMAL(19,4) NULL,
        ItemJson NVARCHAR(MAX) NOT NULL,
        CONSTRAINT FK_InvoiceItems_Invoices FOREIGN KEY (InvoiceId)
            REFERENCES dbo.Invoices(Id) ON DELETE CASCADE
    );
    CREATE INDEX IX_InvoiceItems_InvoiceId ON dbo.InvoiceItems(InvoiceId);
END;
GO

IF OBJECT_ID(N'dbo.InvoiceExtraFields', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.InvoiceExtraFields (
        Id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        InvoiceId UNIQUEIDENTIFIER NOT NULL,
        GroupPath NVARCHAR(500) NOT NULL,
        FieldName NVARCHAR(500) NULL,
        DataType NVARCHAR(100) NULL,
        FieldValue NVARCHAR(MAX) NULL,
        CONSTRAINT FK_InvoiceExtraFields_Invoices FOREIGN KEY (InvoiceId)
            REFERENCES dbo.Invoices(Id) ON DELETE CASCADE
    );
    CREATE INDEX IX_InvoiceExtraFields_InvoiceId ON dbo.InvoiceExtraFields(InvoiceId);
END;
GO
