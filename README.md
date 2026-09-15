# Chạy Receipt Reader trên Windows

## Chuẩn bị

Cài Python 3.12–3.14 và Node.js 22. Nếu dùng Tesseract, cài [Tesseract OCR 5](https://tesseract-ocr.github.io/tessdoc/Installation.html) cùng gói ngôn ngữ Vietnamese (`vie`) và English (`eng`). Nếu chỉ dùng Google Cloud Vision, làm thêm bước cấu hình Vision bên dưới.

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

## Tùy chọn chạy OCR bằng Google Cloud Vision

Áp dụng cho cả SQLite và SQL Server. Cấu hình quyền Google Cloud theo [GOOGLE_VISION.md](GOOGLE_VISION.md), rồi chạy các lệnh sau trong cửa sổ backend trước khi chạy `backend/run.py`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.vision.txt
$env:GOOGLE_VISION_ENABLED = "true"
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\private\vision-service-account.json"
```

Trên giao diện, bật OCR rồi chọn **Google Cloud Vision**. Engine này chạy độc lập, không cần Tesseract để nhận dạng. Bỏ qua cấu hình này nếu chỉ dùng Tesseract.

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
