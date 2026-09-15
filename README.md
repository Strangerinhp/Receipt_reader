# Chạy Receipt Reader trên Windows

## Chuẩn bị

Cài Python 3.12–3.14, Node.js 22 và [Tesseract OCR 5](https://tesseract-ocr.github.io/tessdoc/Installation.html) cùng gói ngôn ngữ Vietnamese (`vie`) và English (`eng`). Tạo API key tại [Mistral AI Studio](https://console.mistral.ai/api-keys) nếu muốn chọn Mistral OCR.

Mở PowerShell tại thư mục repository và tạo môi trường Python:

```powershell
python -m venv .venv
```

Chọn **một** trong hai cách chạy backend bên dưới, sau đó chạy frontend ở cửa sổ PowerShell thứ hai.

## Lựa chọn 1: SQLite

Từ thư mục repository:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.sqlite.txt
$env:DATABASE_ENGINE = "sqlite"
$env:SQLITE_DATABASE_PATH = "$PWD/backend/data/invoice_ocr.db"
$env:AUTO_INIT_DB = "true"
$env:FRONTEND_ORIGIN = "http://localhost:3000"
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:PORT = "5000"
.\.venv\Scripts\python.exe backend/run.py
```

Sửa TESSERACT_CMD nếu Tesseract được cài ở vị trí khác. Database và bảng được tạo tự động trong backend/data/.

## Lựa chọn 2: Microsoft SQL Server

Cài SQL Server và [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server). Khởi động dịch vụ SQL Server. Trong SSMS, kết nối tới instance bạn sử dụng và chạy một lần nếu chưa có database:

```sql
CREATE DATABASE InvoiceOCR;
```

Từ thư mục repository, chạy backend với Windows Authentication:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
$env:DATABASE_ENGINE = "sqlserver"
$env:SQLSERVER_CONNECTION_STRING = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=InvoiceOCR;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes"
$env:AUTO_INIT_DB = "true"
$env:FRONTEND_ORIGIN = "http://localhost:3000"
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:PORT = "5000"
.\.venv\Scripts\python.exe backend/run.py
```

Đổi SERVER=localhost thành instance thực tế, ví dụ SERVER=localhost\SQLEXPRESS. Tài khoản Windows chạy backend cần quyền đọc/ghi và tạo bảng trong InvoiceOCR. App tạo bảng tự động, không tự tạo database SQL Server.

Nếu dùng SQL Authentication, bật chế độ đăng nhập SQL Server và thay connection string trước khi chạy backend:

```powershell
$env:SQLSERVER_CONNECTION_STRING = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=InvoiceOCR;UID=invoice_app;PWD=YOUR_PASSWORD;Encrypt=yes;TrustServerCertificate=yes"
```

## Tùy chọn Mistral OCR

SDK Mistral đã nằm trong requirements chung, không cần cài thêm file requirements. Trước khi chạy backend, có thể đặt API key trong PowerShell:

```powershell
$env:MISTRAL_API_KEY = "your_mistral_api_key"
```

Hoặc thêm `MISTRAL_API_KEY=...` vào `backend/.env`. Không commit API key. Trên giao diện, Tesseract vẫn được chọn mặc định; bật OCR và chọn **Mistral OCR** khi muốn gửi file tới dịch vụ Mistral. Không có cờ bật dịch vụ riêng. Nếu chọn Mistral mà chưa có key, tác vụ sẽ báo lỗi cấu hình.

## Chạy frontend và mở ứng dụng

Mở PowerShell thứ hai tại thư mục repository:

```powershell
cd frontend
npm.cmd ci --legacy-peer-deps --no-audit --no-fund
$env:REACT_APP_BACKEND_URL = "http://localhost:5000/api"
$env:PORT = "3000"
npm.cmd start
```

Mở **http://localhost:3000**. Kiểm tra backend tại **http://localhost:5000/api/health**. Giữ hai cửa sổ PowerShell mở; nhấn Ctrl+C ở từng cửa sổ để dừng. Dữ liệu đã lưu vẫn còn sau khi dừng ứng dụng.
