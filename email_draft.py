"""Build a quote email and open it in the default mail app."""

from __future__ import annotations

import base64
import os
import re
import tempfile
from email import policy
from email.message import EmailMessage
from pathlib import Path


def _plain(text: str) -> str:
    return (
        (text or "")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def _first_name(full_name: str) -> str:
    name = (full_name or "").strip()
    if not name:
        return "there"
    return name.split()[0]


def _window_phrase(qty: float | int) -> str:
    count = int(qty or 0)
    if count == 1:
        return "1 window"
    return f"{count} windows"


def compose_email(quote: dict, catalog: dict) -> dict:
    client = quote.get("client") or {}
    company = catalog.get("company") or {}
    name = _plain(str(client.get("name") or "").strip())
    first = _first_name(name)
    qty = quote.get("qty_total") or 0
    notes = _plain(str(quote.get("notes") or "").strip())
    company_name = _plain(str(company.get("name") or "Erskine & Sons"))
    phone = _plain(str(company.get("phone") or ""))
    website = _plain(str(company.get("website") or "")).replace("https://", "").replace("http://", "").rstrip("/")

    greeting_name = name or first
    windows = _window_phrase(qty)

    lines = [
        f"Hi {first},",
        "",
        f"Thank you for the chance to quote your glass work. I have a quote ready for {windows}. The PDF is attached for you to look over.",
    ]
    if notes:
        lines.extend(["", f"Job notes: {notes}"])
    lines.extend(
        [
            "",
            "Please take a look and let me know if you would like any sizes or glass types changed. I am happy to walk through the details if that would help.",
            "",
            "Thanks,",
            "David Erskine",
            company_name,
        ]
    )
    if phone:
        lines.append(phone)
    if website:
        lines.append(website)

    body = _plain("\n".join(lines))
    if name:
        subject = _plain(f"Glass quote for {name}")
    else:
        subject = "Glass quote"
    return {
        "to": str(client.get("email") or "").strip(),
        "subject": subject,
        "body": body,
        "filename": f"{(name or 'quote').replace(' ', '_')}_quote.pdf",
    }


def build_eml(draft: dict, pdf_bytes: bytes) -> bytes:
    msg = EmailMessage()
    if draft.get("to"):
        msg["To"] = draft["to"]
    msg["Subject"] = draft.get("subject") or "Glass quote"
    msg["X-Unsent"] = "1"
    msg.set_content(draft.get("body") or "", charset="utf-8", cte="8bit")
    filename = draft.get("filename") or "quote.pdf"
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )
    return msg.as_bytes(policy=policy.SMTP.clone(max_line_length=0))


def open_eml(eml_bytes: bytes, stem: str = "erskine_quote") -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem) or "erskine_quote"
    path = Path(tempfile.gettempdir()) / f"{safe}.eml"
    path.write_bytes(eml_bytes)
    os.startfile(path)  # noqa: S606 - local desktop helper
    return path
