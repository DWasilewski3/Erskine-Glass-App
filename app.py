"""Erskine & Sons local quote app."""

from __future__ import annotations

import threading
import webbrowser
from datetime import date, datetime
from pathlib import Path

import io

from flask import Flask, jsonify, render_template, request, send_file

import email_draft
import exporters
import quote_engine
import storage

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


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


@app.post("/api/email")
def api_email():
    quote, catalog = _incoming_quote()
    client = quote.get("client") or {}
    if not (client.get("name") or "").strip():
        return _json_error("Select or add a client first.")
    pdf = exporters.build_pdf(quote, catalog)
    draft = email_draft.compose_email(quote, catalog)
    eml = email_draft.build_eml(draft, pdf)
    opened = False
    error = ""
    try:
        stem = f"{client.get('name') or 'quote'}_{quote.get('quote_number') or quote.get('date') or 'draft'}"
        email_draft.open_eml(eml, stem)
        opened = True
    except OSError as exc:
        error = str(exc)
    return jsonify(
        {
            "ok": True,
            "to": draft["to"],
            "subject": draft["subject"],
            "body": draft["body"],
            "opened": opened,
            "error": error,
        }
    )


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(0.8, _open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
