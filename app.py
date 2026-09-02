"""Erskine & Sons local quote app."""

from __future__ import annotations

import threading
import webbrowser
from datetime import date, datetime
from pathlib import Path

import io

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

import email_draft
import exporters
import quote_engine
import resend_client
import storage

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
FROM_ADDRESS = "erskineson@erskineson.com"


def _json_error(message: str, status: int = 400, code: str | None = None):
    payload = {"error": message}
    if code:
        payload["code"] = code
    return jsonify(payload), status


def _incoming_quote() -> dict:
    payload = request.get_json(force=True, silent=True) or {}
    catalog = storage.load_catalog()
    client_id = payload.get("client_id") or ""
    client = storage.get_client(client_id) if client_id else None
    if not client:
        client = {
            "id": "",
            "name": str(payload.get("client_name") or "").strip(),
            "phone": str(payload.get("client_phone") or "").strip(),
            "email": str(payload.get("client_email") or "").strip(),
            "address": str(payload.get("client_address") or "").strip(),
            "notes": str(payload.get("client_notes") or "").strip(),
        }
    quote = {
        "client_id": client.get("id") or "",
        "client": client,
        "date": payload.get("date") or date.today().isoformat(),
        "notes": str(payload.get("notes") or "").strip(),
        "lines": payload.get("lines") or [],
        "quote_number": payload.get("quote_number") or "",
        "folder": payload.get("folder") or "",
    }
    return quote_engine.price_quote(quote, catalog), catalog


@app.get("/")
def quote_page():
    catalog = storage.load_catalog()
    return render_template(
        "quote.html",
        catalog=catalog,
        clients=storage.load_clients(),
        today=date.today().isoformat(),
    )


@app.get("/settings")
def settings_page():
    return render_template(
        "settings.html",
        catalog=storage.load_catalog(),
        clients=storage.load_clients(),
    )


@app.get("/api/catalog")
def api_catalog():
    return jsonify(storage.load_catalog())


@app.post("/api/catalog")
def api_save_catalog():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(storage.save_catalog(payload))


@app.get("/api/clients")
def api_clients():
    return jsonify(storage.load_clients())


@app.post("/api/clients")
def api_add_client():
    try:
        return jsonify(storage.add_client(request.get_json(force=True, silent=True) or {}))
    except ValueError as exc:
        return _json_error(str(exc))


@app.put("/api/clients/<client_id>")
def api_update_client(client_id: str):
    try:
        return jsonify(storage.update_client(client_id, request.get_json(force=True, silent=True) or {}))
    except KeyError:
        return _json_error("Client not found.", 404)


@app.delete("/api/clients/<client_id>")
def api_delete_client(client_id: str):
    storage.delete_client(client_id)
    return jsonify({"ok": True})


@app.post("/api/calculate")
def api_calculate():
    quote, _catalog = _incoming_quote()
    return jsonify(quote)


@app.get("/api/last-quote")
def api_last_quote():
    return jsonify(storage.load_last_quote() or {})


@app.post("/api/last-quote")
def api_save_last_quote():
    quote, _catalog = _incoming_quote()
    storage.save_last_quote(quote)
    return jsonify({"ok": True})


@app.get("/api/quotes/<client_id>")
def api_list_quotes(client_id: str):
    return jsonify(storage.list_quotes(client_id))


@app.get("/api/quotes/<client_id>/<folder>")
def api_load_quote(client_id: str, folder: str):
    try:
        return jsonify(storage.load_quote(client_id, folder))
    except FileNotFoundError:
        return _json_error("Quote not found.", 404)


@app.post("/api/quotes/save")
def api_save_quote():
    quote, catalog = _incoming_quote()
    client = quote.get("client") or {}
    if not client.get("id"):
        return _json_error("Select or add a client before saving.")
    folder, folder_name, quote_number = storage.next_quote_folder(
        client["id"], quote.get("date")
    )
    quote["quote_number"] = quote_number
    quote["folder"] = folder_name
    quote["saved_at"] = datetime.now().isoformat(timespec="seconds")
    storage.save_quote_json(folder, quote)
    (folder / "quote.pdf").write_bytes(exporters.build_pdf(quote, catalog))
    (folder / "quote.xlsx").write_bytes(exporters.build_xlsx(quote, catalog))
    (folder / "quote.csv").write_text(exporters.build_csv(quote), encoding="utf-8-sig")
    (folder / "glass_needed.csv").write_text(
        exporters.build_glass_needed_csv(quote), encoding="utf-8-sig"
    )
    (folder / "glass_needed.pdf").write_bytes(exporters.build_glass_needed_pdf(quote, catalog))
    storage.save_last_quote(quote)
    return jsonify(
        {
            "ok": True,
            "quote": quote,
            "folder": folder_name,
            "path": str(folder),
        }
    )


def _download(filename: str, data: bytes, mime: str):
    buf = io.BytesIO(data)
    buf.seek(0)
    return send_file(buf, mimetype=mime, as_attachment=True, download_name=filename)


@app.post("/api/export/pdf")
def api_export_pdf():
    quote, catalog = _incoming_quote()
    name = (quote.get("client") or {}).get("name") or "quote"
    number = quote.get("quote_number") or quote.get("date") or "quote"
    return _download(
        f"{name}_{number}.pdf".replace(" ", "_"),
        exporters.build_pdf(quote, catalog),
        "application/pdf",
    )


@app.post("/api/export/xlsx")
def api_export_xlsx():
    quote, catalog = _incoming_quote()
    name = (quote.get("client") or {}).get("name") or "quote"
    number = quote.get("quote_number") or quote.get("date") or "quote"
    return _download(
        f"{name}_{number}.xlsx".replace(" ", "_"),
        exporters.build_xlsx(quote, catalog),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/api/export/csv")
def api_export_csv():
    quote, _catalog = _incoming_quote()
    name = (quote.get("client") or {}).get("name") or "quote"
    number = quote.get("quote_number") or quote.get("date") or "quote"
    data = exporters.build_csv(quote).encode("utf-8-sig")
    return _download(f"{name}_{number}.csv".replace(" ", "_"), data, "text/csv")


@app.post("/api/export/glass-needed")
def api_export_glass_needed():
    quote, _catalog = _incoming_quote()
    name = (quote.get("client") or {}).get("name") or "quote"
    number = quote.get("quote_number") or quote.get("date") or "quote"
    data = exporters.build_glass_needed_csv(quote).encode("utf-8-sig")
    return _download(
        f"{name}_{number}_glass_needed.csv".replace(" ", "_"),
        data,
        "text/csv",
    )


@app.post("/api/export/glass-needed-pdf")
def api_export_glass_needed_pdf():
    quote, catalog = _incoming_quote()
    name = (quote.get("client") or {}).get("name") or "quote"
    number = quote.get("quote_number") or quote.get("date") or "quote"
    return _download(
        f"{name}_{number}_glass_needed.pdf".replace(" ", "_"),
        exporters.build_glass_needed_pdf(quote, catalog),
        "application/pdf",
    )


def _require_client(quote: dict) -> dict:
    client = quote.get("client") or {}
    if not (client.get("name") or "").strip():
        raise resend_client.ResendError("Select or add a client first.")
    return client


def _pdf_filename(quote: dict, suffix: str = "") -> str:
    name = ((quote.get("client") or {}).get("name") or "quote").replace(" ", "_")
    number = quote.get("quote_number") or quote.get("date") or "quote"
    extra = f"_{suffix}" if suffix else ""
    return f"{name}_{number}{extra}.pdf"


def _send_email(draft: dict, pdf_bytes: bytes, pdf_name: str) -> str:
    if not resend_client.is_configured():
        raise resend_client.ResendError(
            "Resend API key is not set. Add it in Settings.",
            status=503,
            code="not_configured",
        )
    to = str(draft.get("to") or "").strip()
    resend_client.send_email(
        to=to,
        subject=str(draft.get("subject") or ""),
        body=str(draft.get("body") or ""),
        from_address=FROM_ADDRESS,
        attachment=(pdf_name, pdf_bytes),
    )
    return to


@app.post("/api/email")
def api_email():
    quote, catalog = _incoming_quote()
    try:
        _require_client(quote)
    except resend_client.ResendError as exc:
        return _json_error(str(exc), exc.status, exc.code)
    draft = email_draft.compose_email(quote, catalog)
    return jsonify({"ok": True, **draft})


@app.post("/api/email/manufacturer")
def api_email_manufacturer():
    quote, catalog = _incoming_quote()
    try:
        _require_client(quote)
    except resend_client.ResendError as exc:
        return _json_error(str(exc), exc.status, exc.code)
    draft = email_draft.compose_manufacturer_email(quote, catalog)
    return jsonify({"ok": True, **draft})


@app.post("/api/email/send")
def api_email_send():
    try:
        quote, catalog = _incoming_quote()
        _require_client(quote)
        draft = email_draft.compose_email(quote, catalog)
        pdf = exporters.build_pdf(quote, catalog)
        to = _send_email(draft, pdf, _pdf_filename(quote))
        return jsonify({"ok": True, "to": to, "message": f"Email sent to {to}."})
    except resend_client.ResendError as exc:
        return _json_error(str(exc), exc.status, exc.code)
    except Exception as exc:
        return _json_error(f"Could not send email: {exc}", 502)


@app.post("/api/email/send-manufacturer")
def api_email_send_manufacturer():
    try:
        quote, catalog = _incoming_quote()
        _require_client(quote)
        draft = email_draft.compose_manufacturer_email(quote, catalog)
        pdf = exporters.build_glass_needed_pdf(quote, catalog)
        to = _send_email(draft, pdf, _pdf_filename(quote, "glass_needed"))
        return jsonify({"ok": True, "to": to, "message": f"Email sent to {to}."})
    except resend_client.ResendError as exc:
        return _json_error(str(exc), exc.status, exc.code)
    except Exception as exc:
        return _json_error(f"Could not send email: {exc}", 502)


@app.get("/api/resend/status")
def api_resend_status():
    payload = resend_client.status()
    if payload.get("configured") and request.args.get("verify") == "1":
        payload.update(resend_client.verify_connection())
    return jsonify(payload)


@app.post("/api/resend/key")
def api_resend_key():
    payload = request.get_json(force=True, silent=True) or {}
    key = str(payload.get("key") or "").strip()
    saved = resend_client.save_api_key(key)
    verified = {"verified": False, "error": ""}
    if saved.get("configured"):
        verified = resend_client.verify_connection()
    return jsonify({"ok": True, **saved, **verified})


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(0.8, _open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
