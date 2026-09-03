"""Resend REST client for quote and manufacturer emails."""

from __future__ import annotations

import base64
import html
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
API_BASE = "https://api.resend.com"
API_KEY_NAME = "RESEND_API_KEY"
LEGACY_KEY_NAME = "THRYV_API_KEY"
TIMEOUT = 30

load_dotenv(ENV_PATH)


class ResendError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "resend_error"):
        super().__init__(message)
        self.status = status
        self.code = code


def _api_key() -> str:
    return str(os.environ.get(API_KEY_NAME) or "").strip()


def is_configured() -> bool:
    return bool(_api_key())


def key_hint(key: str | None = None) -> str:
    value = (key if key is not None else _api_key()).strip()
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return ("•" * max(8, len(value) - 4)) + value[-4:]


def status() -> dict:
    configured = is_configured()
    return {
        "configured": configured,
        "key_hint": key_hint() if configured else "",
    }


def _env_value(value: str) -> str:
    if re.search(r"[\s#=\"']", value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def save_api_key(key: str) -> dict:
    value = (key or "").strip()
    lines: list[str] = []
    found = False
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if re.match(rf"^\s*{re.escape(LEGACY_KEY_NAME)}\s*=", line):
                continue
            if re.match(rf"^\s*{re.escape(API_KEY_NAME)}\s*=", line):
                lines.append(f"{API_KEY_NAME}={_env_value(value)}")
                found = True
            else:
                lines.append(line)
    if not found:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"{API_KEY_NAME}={_env_value(value)}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[API_KEY_NAME] = value
    os.environ.pop(LEGACY_KEY_NAME, None)
    return status()


def _headers() -> dict:
    key = _api_key()
    if not key:
        raise ResendError(
            "Resend API key is not set. Add it in Settings.",
            status=503,
            code="not_configured",
        )
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _error_message(response: requests.Response, fallback: str) -> str:
    try:
        data = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text[:400] if text else fallback
    if not isinstance(data, dict):
        return fallback
    msg = data.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    err = data.get("error")
    if isinstance(err, str) and err.strip():
        return err.strip()
    if isinstance(err, dict):
        nested = err.get("message") or err.get("name")
        if nested:
            return str(nested).strip()
    return fallback


def _raise_for_status(response: requests.Response, action: str) -> None:
    if response.ok:
        return
    fallback = f"Resend could not {action} (HTTP {response.status_code})."
    message = _error_message(response, fallback)
    lowered = message.lower()
    if response.status_code in (401, 403):
        raise ResendError(
            "Resend rejected the API key. Create a key at resend.com/api-keys and paste it in Settings.",
            status=response.status_code,
            code="unauthorized",
        )
    if "domain" in lowered or "not verified" in lowered or "from" in lowered:
        raise ResendError(
            "Resend could not send from erskineson@erskineson.com. "
            "Verify that domain in the Resend dashboard (Domains).",
            status=400,
            code="from_address",
        )
    raise ResendError(message, status=min(max(response.status_code, 400), 502))


def _request(method: str, path: str, action: str, **kwargs) -> dict | list | None:
    url = f"{API_BASE}{path}"
    try:
        response = requests.request(
            method,
            url,
            headers=_headers(),
            timeout=TIMEOUT,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise ResendError(f"Could not reach Resend: {exc}", status=502, code="network") from exc
    _raise_for_status(response, action)
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {}


def verify_connection() -> dict:
    if not is_configured():
        return {"verified": False, "error": "Resend API key is not set."}
    url = f"{API_BASE}/domains"
    try:
        response = requests.get(url, headers=_headers(), timeout=TIMEOUT)
    except requests.RequestException as exc:
        return {"verified": False, "error": f"Could not reach Resend: {exc}"}
    if response.ok:
        return {"verified": True, "error": ""}
    name = ""
    try:
        data = response.json()
        if isinstance(data, dict):
            name = str(data.get("name") or "")
    except ValueError:
        data = {}
    if name == "restricted_api_key":
        # Sending-only keys cannot list domains, but they can send mail.
        return {"verified": True, "error": ""}
    try:
        _raise_for_status(response, "verify the API key")
    except ResendError as exc:
        return {"verified": False, "error": str(exc)}
    return {"verified": False, "error": "Resend rejected the API key."}


def _html_from_plain(body: str) -> str:
    escaped = html.escape(body or "").replace("\r\n", "\n").replace("\n", "<br>\n")
    return (
        "<html><body style=\"font-family:Segoe UI,Arial,sans-serif;"
        "font-size:14px;color:#1a1612;line-height:1.45\">"
        f"{escaped}</body></html>"
    )


def send_email(
    to: str,
    subject: str,
    body: str,
    from_address: str,
    from_name: str = "Erskine & Sons",
    attachment: tuple[str, bytes] | None = None,
) -> dict:
    address = (to or "").strip()
    if not address or "@" not in address:
        raise ResendError("The recipient needs an email address.")
    sender = from_address
    name = (from_name or "").strip()
    if name:
        sender = f"{name} <{from_address}>"
    payload: dict = {
        "from": sender,
        "to": [address],
        "subject": subject or "",
        "text": body or "",
        "html": _html_from_plain(body),
    }
    if attachment:
        filename, data = attachment
        if not data:
            raise ResendError("The PDF attachment is empty.")
        payload["attachments"] = [
            {
                "filename": filename,
                "content": base64.b64encode(data).decode("ascii"),
            }
        ]
    result = _request("POST", "/emails", "send the email", json=payload)
    return result if isinstance(result, dict) else {"ok": True}
