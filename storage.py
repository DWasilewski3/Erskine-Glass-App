"""Local client list and dated per-client quote folders."""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"
CLIENTS_PATH = DATA_DIR / "clients.json"
LAST_QUOTE_PATH = DATA_DIR / "last_quote.json"
QUOTES_DIR = DATA_DIR / "quotes"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    tmp.replace(path)


def load_catalog() -> dict:
    return _read_json(CATALOG_PATH, {})


def save_catalog(catalog: dict) -> dict:
    _write_json(CATALOG_PATH, catalog)
    return catalog


def load_clients() -> list[dict]:
    clients = _read_json(CLIENTS_PATH, [])
    return sorted(clients, key=lambda c: str(c.get("name", "")).lower())


def save_clients(clients: list[dict]) -> list[dict]:
    _write_json(CLIENTS_PATH, clients)
    return load_clients()


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug or "client"


def _unique_slug(name: str, existing: set[str]) -> str:
    base = slugify(name)
    slug = base
    n = 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    return slug


def add_client(payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Client name is required.")
    clients = _read_json(CLIENTS_PATH, [])
    slug = _unique_slug(name, {c.get("id", "") for c in clients})
    client = {
        "id": slug,
        "name": name,
        "phone": str(payload.get("phone") or "").strip(),
        "email": str(payload.get("email") or "").strip(),
        "address": str(payload.get("address") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
    }
    clients.append(client)
    save_clients(clients)
    (QUOTES_DIR / client["id"]).mkdir(parents=True, exist_ok=True)
    return client


def update_client(client_id: str, payload: dict) -> dict:
    clients = _read_json(CLIENTS_PATH, [])
    for client in clients:
        if client.get("id") == client_id:
            if payload.get("name"):
                client["name"] = str(payload["name"]).strip()
            for field in ("phone", "email", "address", "notes"):
                if field in payload:
                    client[field] = str(payload.get(field) or "").strip()
            save_clients(clients)
            return client
    raise KeyError(f"Unknown client: {client_id}")


def delete_client(client_id: str) -> None:
    clients = [c for c in _read_json(CLIENTS_PATH, []) if c.get("id") != client_id]
    save_clients(clients)


def get_client(client_id: str) -> dict | None:
    for client in _read_json(CLIENTS_PATH, []):
        if client.get("id") == client_id:
            return client
    return None


def next_quote_folder(client_id: str, quote_date: str | None = None) -> tuple[Path, str, str]:
    """Return (folder, folder_name, quote_number)."""
    day = quote_date or date.today().isoformat()
    client_dir = QUOTES_DIR / client_id
    client_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{day}_"
    existing = [
        p.name
        for p in client_dir.iterdir()
        if p.is_dir() and p.name.startswith(prefix)
    ]
    seq = 1
    for name in existing:
        try:
            seq = max(seq, int(name.split("_")[-1]) + 1)
        except ValueError:
            continue
    folder_name = f"{prefix}{seq:03d}"
    quote_number = f"{day.replace('-', '')}-{seq:03d}"
    folder = client_dir / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder, folder_name, quote_number


def save_quote_json(folder: Path, quote: dict) -> Path:
    path = folder / "quote.json"
    _write_json(path, quote)
    return path


def list_quotes(client_id: str) -> list[dict]:
    client_dir = QUOTES_DIR / client_id
    if not client_dir.exists():
        return []
    items = []
    for folder in sorted(client_dir.iterdir(), reverse=True):
        json_path = folder / "quote.json"
        if not folder.is_dir() or not json_path.exists():
            continue
        data = _read_json(json_path, {})
        items.append(
            {
                "folder": folder.name,
                "path": str(folder),
                "quote_number": data.get("quote_number") or folder.name,
                "date": data.get("date"),
                "grand_total": data.get("grand_total"),
                "client_name": (data.get("client") or {}).get("name"),
                "saved_at": data.get("saved_at"),
            }
        )
    return items


def load_quote(client_id: str, folder_name: str) -> dict:
    path = QUOTES_DIR / client_id / folder_name / "quote.json"
    if not path.exists():
        raise FileNotFoundError(folder_name)
    return _read_json(path, {})


def quote_folder(client_id: str, folder_name: str) -> Path:
    return QUOTES_DIR / client_id / folder_name


def load_last_quote() -> dict | None:
    data = _read_json(LAST_QUOTE_PATH, None)
    return data if isinstance(data, dict) else None


def save_last_quote(quote: dict) -> None:
    payload = dict(quote)
    payload["saved_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json(LAST_QUOTE_PATH, payload)


def new_quote_id() -> str:
    return uuid.uuid4().hex[:10]
