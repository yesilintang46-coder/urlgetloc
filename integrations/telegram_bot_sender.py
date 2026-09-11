"""Simple Telegram bot sender for hosted notifications.

Set environment variables before use:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import parse, request


TELEGRAM_API_BASE = "https://api.telegram.org"


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _telegram_request(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = _env("TELEGRAM_BOT_TOKEN")
    url = f"{TELEGRAM_API_BASE}/bot{token}/{method}"

    body = parse.urlencode(payload).encode("utf-8")
    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data


def send_text_message(text: str, chat_id: str | None = None) -> dict[str, Any]:
    """Send plain text message to Telegram chat."""
    target_chat = chat_id or _env("TELEGRAM_CHAT_ID")
    payload = {
        "chat_id": target_chat,
        "text": text,
        "disable_web_page_preview": "true",
    }
    return _telegram_request("sendMessage", payload)


def send_capture_summary(
    latitude: float | None,
    longitude: float | None,
    accuracy: float | None,
    file_path: str | None,
    capture_date: str | None,
    device_make: str | None,
    device_model: str | None,
    chat_id: str | None = None,
) -> dict[str, Any]:
    """Send formatted summary message for uploaded mobile capture."""
    maps_url = "unknown"
    if latitude is not None and longitude is not None:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

    lines = [
        "[Mobile Capture]",
        f"Date: {capture_date or 'unknown'}",
        f"Device: {(device_make or 'unknown')} {(device_model or '').strip()}".strip(),
        f"Latitude: {latitude if latitude is not None else 'unknown'}",
        f"Longitude: {longitude if longitude is not None else 'unknown'}",
        f"Accuracy: {accuracy if accuracy is not None else 'unknown'}",
        f"File: {file_path or 'GPS-only'}",
        f"Maps: {maps_url}",
    ]

    return send_text_message("\n".join(lines), chat_id=chat_id)


def send_photo_file(photo_path: str, caption: str = "", chat_id: str | None = None) -> dict[str, Any]:
    """Send photo using Telegram sendPhoto with multipart form-data."""
    token = _env("TELEGRAM_BOT_TOKEN")
    target_chat = chat_id or _env("TELEGRAM_CHAT_ID")

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendPhoto"
    path = Path(photo_path)
    if not path.exists():
        raise FileNotFoundError(f"Photo not found: {photo_path}")

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()

    def add_field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    add_field("chat_id", target_chat)
    if caption:
        add_field("caption", caption)

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f"Content-Disposition: form-data; name=\"photo\"; filename=\"{path.name}\"\r\n".encode("utf-8")
    )
    body.extend(b"Content-Type: image/jpeg\r\n\r\n")
    body.extend(path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    with request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data


if __name__ == "__main__":
    # Example quick manual test:
    # TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python integrations/telegram_bot_sender.py
    result = send_text_message("Test message from urlgetloc host")
    print(result)
