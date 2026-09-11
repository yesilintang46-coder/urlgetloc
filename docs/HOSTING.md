# Hosting Guide

## 1. Current Project Layout

- `src/cekfoto.py`: main app logic and local server.
- `web/index.html`: mobile capture page (style and JS).
- `tests/test_gps_flow.py`: flow test for upload endpoint.
- `data/captures/`: webcam captures.
- `data/captures_phone/`: mobile uploads and GPS sidecar JSON.
- `data/captures_phone/ssl/`: local self-signed cert files.

## 2. Install Dependencies

Use your virtual environment, then install:

```bash
pip install pillow piexif
```

Optional:

```bash
pip install pillow-heif opencv-python
```

## 3. Run Local (Self-Signed HTTPS)

Self-signed local HTTPS is enabled by default.

```bash
python src/cekfoto.py
```

Then type `phone` in the CLI prompt.

## 4. Run For Hosted Deployment

If HTTPS is already handled by hosting/reverse proxy (Nginx, Caddy, Cloudflare, etc), disable local SSL wrapper:

```bash
USE_LOCAL_HTTPS=0 python src/cekfoto.py
```

Important: browser camera and geolocation still require HTTPS at the public URL.

## 5. What To Disable/Comment In Hosted Mode

No code edits are required if you use `USE_LOCAL_HTTPS=0`.

If you still want manual comment markers in `src/cekfoto.py`, these are the local-SSL related parts:

- Function call in `main()`:
  - `port = _start_server_mobile(directory=str(WEB_DIR), port=8000, use_https=use_local_https)`
- SSL wrapper inside `_start_server_mobile(...)`:
  - `if use_https:` block that calls `_ensure_https_certificate()` and wraps socket with `ssl.SSLContext`.

Recommended approach: keep code as-is and control with env var.

## 6. Reverse Proxy Notes

- Public endpoint should serve `https://your-domain/index.html`.
- Reverse proxy forwards `POST /upload-json` to Python app port.
- Keep upload body size limit large enough for base64 image payload.

Example Nginx snippets (conceptual):

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
}

location /upload-json {
    client_max_body_size 20m;
    proxy_pass http://127.0.0.1:8000;
}
```

## 7. Quick Verification

From project root:

```bash
python tests/test_gps_flow.py
```

Expected result:
- Server starts.
- Upload request returns JSON with `ok: true`.
- New files appear in `data/captures_phone/`.

## 8. Telegram Notification (After Hosting)

Set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="<your-bot-token>"
export TELEGRAM_CHAT_ID="<your-chat-id>"
```

Quick test:

```bash
python integrations/telegram_bot_sender.py
```

Code snippet to use after an upload is saved:

```python
from integrations.telegram_bot_sender import send_capture_summary

send_capture_summary(
  latitude=gps_data.get("latitude") if gps_data else None,
  longitude=gps_data.get("longitude") if gps_data else None,
  accuracy=gps_data.get("accuracy") if gps_data else None,
  file_path=saved_path,
  capture_date=capture_date,
  device_make=(device_data or {}).get("make"),
  device_model=(device_data or {}).get("model"),
)
```
