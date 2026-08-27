"""Build a quote email and open it in the default mail app."""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import tempfile
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import policy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGO_PNG = ROOT / "static" / "img" / "logo.png"
MANUFACTURER_EMAIL = "kbloink@trulite.com"
LOGO_CID = "logo.png"


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


def compose_manufacturer_email(quote: dict, catalog: dict) -> dict:
    client = quote.get("client") or {}
    company = catalog.get("company") or {}
    manufacturer = catalog.get("manufacturer") or {}
    name = _plain(str(client.get("name") or "").strip())
    qty = quote.get("qty_total") or 0
    notes = _plain(str(quote.get("notes") or "").strip())
    company_name = _plain(str(company.get("name") or "Erskine & Sons"))
    phone = _plain(str(company.get("phone") or ""))
    website = _plain(str(company.get("website") or "")).replace("https://", "").replace("http://", "").rstrip("/")
    to = _plain(str(manufacturer.get("email") or MANUFACTURER_EMAIL)).strip() or MANUFACTURER_EMAIL
    windows = _window_phrase(qty)

    if name:
        intro = (
            f"I have a glass needed list ready for {name} ({windows}). "
            "The PDF is attached for you to look over."
        )
    else:
        intro = (
            f"I have a glass needed list ready for {windows}. "
            "The PDF is attached for you to look over."
        )
    lines = [
        "Hi,",
        "",
        intro,
    ]
    if notes:
        lines.extend(["", f"Job notes: {notes}"])
    lines.extend(
        [
            "",
            "Please take a look and let me know if you have any questions.",
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
        subject = _plain(f"Glass needed for {name}")
    else:
        subject = "Glass needed"
    return {
        "to": to,
        "subject": subject,
        "body": body,
        "filename": f"{(name or 'quote').replace(' ', '_')}_glass_needed.pdf",
    }


def _html_body(plain: str, cid_ref: str | None) -> str:
    escaped = html.escape(plain or "").replace("\n", "<br>\r\n")
    logo = ""
    if cid_ref:
        logo = (
            "<br>\r\n"
            f'<img src="cid:{html.escape(cid_ref)}" alt="Erskine &amp; Sons" '
            'width="147" height="72" '
            'style="display:block;border:0;outline:none;text-decoration:none;'
            'width:147px;height:72px;margin-top:8px;" />'
        )
    return (
        "<!DOCTYPE html>\r\n<html>\r\n<head>"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
        "</head>\r\n<body "
        'style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#000000;">'
        f"{escaped}{logo}"
        "</body>\r\n</html>"
    )


def _text_part(body: str, subtype: str) -> MIMEText:
    part = MIMEText(body, subtype, "utf-8")
    del part["Content-Transfer-Encoding"]
    part.set_payload(body)
    part["Content-Transfer-Encoding"] = "8bit"
    return part


def build_eml(draft: dict, pdf_bytes: bytes) -> bytes:
    filename = draft.get("filename") or "quote.pdf"
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    plain = draft.get("body") or ""
    has_logo = LOGO_PNG.exists()
    html_body = _html_body(plain, LOGO_CID if has_logo else None)

    msg = MIMEMultipart("mixed")
    if draft.get("to"):
        msg["To"] = draft["to"]
    msg["Subject"] = draft.get("subject") or "Glass quote"
    msg["X-Unsent"] = "1"
    msg["MIME-Version"] = "1.0"

    related = MIMEMultipart("related")
    related.set_param("type", "multipart/alternative")
    alt = MIMEMultipart("alternative")
    alt.attach(_text_part(plain.replace("\n", "\r\n"), "plain"))
    alt.attach(_text_part(html_body, "html"))
    related.attach(alt)

    if has_logo:
        image = MIMEImage(LOGO_PNG.read_bytes(), _subtype="png", name="logo.png")
        image.add_header("Content-ID", f"<{LOGO_CID}>")
        image.add_header("Content-Disposition", "inline", filename="logo.png")
        image.add_header("X-Attachment-Id", LOGO_CID)
        related.attach(image)

    msg.attach(related)
    pdf = MIMEApplication(pdf_bytes, _subtype="pdf", name=filename)
    pdf.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(pdf)
    return msg.as_bytes(policy=policy.SMTP)


def _try_outlook(draft: dict, pdf_bytes: bytes) -> bool:
    """Create a real Outlook draft so the inline logo actually displays."""
    if os.name != "nt" or not LOGO_PNG.exists():
        return False
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", draft.get("filename") or "quote.pdf")
    work = Path(tempfile.mkdtemp(prefix="erskine_mail_"))
    pdf_path = work / filename
    pdf_path.write_bytes(pdf_bytes)
    payload = {
        "to": draft.get("to") or "",
        "subject": draft.get("subject") or "Glass quote",
        "html": _html_body(draft.get("body") or "", LOGO_CID),
        "logo": str(LOGO_PNG),
        "pdf": str(pdf_path),
        "cid": LOGO_CID,
    }
    json_path = work / "draft.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8-sig")
    ps1_path = work / "open_draft.ps1"
    ps1_path.write_text(
        "\n".join(
            [
                "param([string]$JsonPath)",
                "$ErrorActionPreference = 'Stop'",
                "$payload = Get-Content -Raw -Encoding UTF8 $JsonPath | ConvertFrom-Json",
                "$ol = New-Object -ComObject Outlook.Application",
                "$mail = $ol.CreateItem(0)",
                "if ($payload.to) { $mail.To = $payload.to }",
                "$mail.Subject = $payload.subject",
                "$mail.BodyFormat = 2",
                "$logo = $mail.Attachments.Add($payload.logo)",
                "$cidProp = 'http://schemas.microsoft.com/mapi/proptag/0x3712001F'",
                "$hiddenProp = 'http://schemas.microsoft.com/mapi/proptag/0x7FFE000B'",
                "$flagsProp = 'http://schemas.microsoft.com/mapi/proptag/0x37140003'",
                "$logo.PropertyAccessor.SetProperty($cidProp, $payload.cid)",
                "try { $logo.PropertyAccessor.SetProperty($hiddenProp, $true) } catch {}",
                "try { $logo.PropertyAccessor.SetProperty($flagsProp, 4) } catch {}",
                "$mail.HTMLBody = $payload.html",
                "[void]$mail.Attachments.Add($payload.pdf)",
                "$mail.Display()",
            ]
        ),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1_path),
                "-JsonPath",
                str(json_path),
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def open_eml(eml_bytes: bytes, stem: str = "erskine_quote") -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem) or "erskine_quote"
    path = Path(tempfile.gettempdir()) / f"{safe}.eml"
    path.write_bytes(eml_bytes)
    os.startfile(path)  # noqa: S606 - local desktop helper
    return path


def open_draft(draft: dict, pdf_bytes: bytes, stem: str = "erskine_quote") -> Path | None:
    if _try_outlook(draft, pdf_bytes):
        return None
    return open_eml(build_eml(draft, pdf_bytes), stem)
