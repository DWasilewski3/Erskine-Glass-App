"""Compose email drafts for quotes and manufacturer orders."""

from __future__ import annotations

MANUFACTURER_EMAIL = "kbloink@trulite.com"


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
    to = str(client.get("email") or "").strip()
    if name:
        subject = _plain(f"Glass quote for {name}")
    else:
        subject = "Glass quote"
    return {
        "to": to,
        "subject": subject,
        "body": body,
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
    }
