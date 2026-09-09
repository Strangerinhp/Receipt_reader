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
