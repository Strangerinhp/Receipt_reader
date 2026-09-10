from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .parser import parse_input


api = Blueprint("api", __name__)


def _repository():
    return current_app.extensions["invoice_repository"]


@api.route("/health", methods=["GET"])
def health():
    repository = _repository()
    return jsonify({
        "status": "ok",
        "database": "configured" if repository.configured else "not_configured",
        "database_engine": repository.engine_name,
    })


@api.route("/invoices/parse", methods=["POST", "OPTIONS"])
def parse_invoice():
    if request.method == "OPTIONS":
        return "", 204
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Vui lòng chọn file."}), 400
    use_ocr = request.form.get("use_ocr", "false").lower() in {"1", "true", "yes", "on"}
    try:
        draft = parse_input(uploaded.filename, uploaded.content_type, uploaded.read(), use_ocr)
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 422
    return jsonify(draft)


@api.route("/invoices/parse-jobs", methods=["POST"])
def submit_parse_job():
    from .parse_jobs import QueueFull
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Vui lòng chọn file."}), 400
    use_ocr = request.form.get("use_ocr", "false").lower() in {"1", "true", "yes", "on"}
    try:
        job_id = current_app.extensions["parse_jobs"].submit(
            uploaded.filename, uploaded.content_type, uploaded.read(), use_ocr)
    except QueueFull:
        return jsonify({"error": "Đang xử lý nhiều hóa đơn. Vui lòng thử lại sau."}), 429
    return jsonify({"id": job_id, "status": "queued"}), 202


@api.route("/invoices/parse-jobs/<job_id>", methods=["GET"])
def get_parse_job(job_id):
    job = current_app.extensions["parse_jobs"].get(job_id, include_result=request.args.get('summary') != '1')
    response = jsonify(job if job else {"error": "Tác vụ không tồn tại hoặc đã hết hạn. Hãy tải lại file."})
    response.headers["Cache-Control"] = "no-store"
    return response, 200 if job else 404


@api.route("/invoices/parse-jobs/<job_id>/result", methods=["GET"])
def get_parse_result(job_id):
    job = current_app.extensions["parse_jobs"].get(job_id)
    if not job:
        return jsonify({"error": "Tác vụ không tồn tại hoặc đã hết hạn."}), 404
    if job['status'] != 'completed':
        return jsonify({"error": job['error'] or "Tác vụ chưa hoàn thành."}), 409
    result = job['result']
    if request.args.get('include_source') == '0':
        result.pop('source_base64', None)
    response = jsonify(result)
    response.headers['Cache-Control'] = 'no-store'
    return response


@api.route("/invoices", methods=["GET", "POST", "OPTIONS"])
def invoices():
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload.get("document"), dict):
            return jsonify({"error": "Thiếu document hợp lệ."}), 400
        try:
            invoice_id = _repository().create(payload)
        except ValueError as exc:
            return jsonify({"error": f"Dữ liệu file không hợp lệ: {exc}"}), 400
        return jsonify({"id": invoice_id, "message": "Đã lưu hóa đơn."}), 201

    query = request.args.get("q", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(100, max(1, request.args.get("page_size", 25, type=int)))
    return jsonify(_repository().list(query, page, page_size))


@api.route("/invoices/<invoice_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
def invoice_detail(invoice_id: str):
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "GET":
        invoice = _repository().get(invoice_id)
        return (jsonify(invoice), 200) if invoice else (jsonify({"error": "Không tìm thấy hóa đơn."}), 404)
    if request.method == "DELETE":
        return ("", 204) if _repository().delete(invoice_id) else (jsonify({"error": "Không tìm thấy hóa đơn."}), 404)

    payload = request.get_json(silent=True) or {}
    document = payload.get("document")
    if not isinstance(document, dict):
        return jsonify({"error": "Thiếu document hợp lệ."}), 400
    try:
        _repository().update(invoice_id, document)
    except KeyError:
        return jsonify({"error": "Không tìm thấy hóa đơn."}), 404
    return jsonify({"message": "Đã cập nhật hóa đơn."})
