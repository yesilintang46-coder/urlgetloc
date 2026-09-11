# Guidebook

This guide explains:
1. How to host this project
2. How to configure Telegram bot notifications

## 1. How To Hosting

### A. Project Structure (important paths)

- `src/cekfoto.py` -> main Python app
- `web/index.html` -> mobile capture page
- `data/captures_phone/` -> uploaded photos + GPS JSON
- `integrations/telegram_bot_sender.py` -> Telegram sender utility

### B. Install dependencies

From project root:

```bash
source .venv/bin/activate
pip install pillow piexif
```

Optional features:

```bash
pip install pillow-heif opencv-python
```

### C. Local run (self-signed HTTPS, default)

```bash
python src/cekfoto.py
```

Then in CLI type:
- `phone` -> open mobile camera flow
- `camera` -> webcam capture

### D. Hosted run (TLS handled by reverse proxy)

For production/reverse proxy setup, disable local SSL wrapper:

```bash
USE_LOCAL_HTTPS=0 python src/cekfoto.py
```

Why: in hosting, HTTPS should be handled by Nginx/Caddy/Cloudflare, not by app self-signed cert.

### E. Reverse proxy essentials

- Public URL should serve: `https://your-domain/index.html`
- Forward requests to Python app (example `127.0.0.1:8000`)
- Ensure upload endpoint is forwarded:
  - `POST /upload-json`
- Increase max request body size (base64 image payload)

Example Nginx idea:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
}

location /upload-json {
    client_max_body_size 20m;
    proxy_pass http://127.0.0.1:8000;
}
```

### F. Basic verification

```bash
python tests/test_gps_flow.py
```

Expected:
- server starts
- upload returns `ok: true`
- new files appear in `data/captures_phone/`

## 2. How To Config Telegram Bot

### A. Create bot and get token

1. Open Telegram and chat with `@BotFather`
2. Run `/newbot`
3. Save the generated bot token

### B. Get chat ID

Quick method:
1. Send a message to your bot from your Telegram account/group
2. Open in browser:
   - `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `chat.id` from the JSON response

### C. Set environment variables

```bash
export TELEGRAM_BOT_TOKEN="<your-bot-token>"
export TELEGRAM_CHAT_ID="<your-chat-id>"
```

Tip: add these to your shell profile or deployment environment variables.

### D. Test Telegram sender

```bash
python integrations/telegram_bot_sender.py
```

If success, Telegram will receive: `Test message from urlgetloc host`.

### E. Use in app flow (send capture summary)

Use this code after upload is processed:

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

### F. Optional: send photo file too

```python
from integrations.telegram_bot_sender import send_photo_file

send_photo_file(
    photo_path=saved_path,
    caption="New mobile capture uploaded"
)
```

## Common Troubleshooting

- `Missing required env var`:
  - ensure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are exported
- Telegram API error `chat not found`:
  - wrong chat ID or bot has never received a message in that chat
- Camera/GPS not working in browser:
  - must use HTTPS on hosted domain
- Upload fails with big payload:
  - increase reverse proxy `client_max_body_size`
