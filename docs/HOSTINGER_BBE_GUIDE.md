# Hostinger Deployment Guide for bbe.com

This guide deploys the app to Hostinger and enables Telegram notifications.

## 1. Decide Hosting Type

- Recommended: Hostinger VPS (full control, systemd + Nginx).
- Shared hosting may not support persistent Python services reliably.

If you are on shared hosting and cannot run a long-lived Python process, use VPS.

## 2. DNS Setup in Hostinger

In domain `bbe.com` DNS zone:

1. Set `A` record:
- Host: `@`
- Value: `<your-vps-public-ip>`
2. Set `A` record for `www`:
- Host: `www`
- Value: `<your-vps-public-ip>`

Wait propagation, then test:

```bash
ping bbe.com
```

## 3. Upload Project to Server

SSH into VPS and clone:

```bash
git clone https://github.com/yesilintang46-coder/urlgetloc.git
cd urlgetloc
```

## 4. Create Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Configure Environment Variables

Create `.env` from template:

```bash
cp .env.example .env
```

Edit `.env` and fill Telegram values:

```env
APP_HOST=0.0.0.0
APP_PORT=8000
USE_LOCAL_HTTPS=0

TELEGRAM_NOTIFY_ENABLED=1
TELEGRAM_BOT_TOKEN=<YOUR_TOKEN>
TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
TELEGRAM_SEND_PHOTO=0
```

Notes:
- Keep `.env` private.
- `USE_LOCAL_HTTPS=0` because HTTPS will be handled by Nginx + SSL cert.

## 6. Run App Manually (quick test)

```bash
set -a
source .env
set +a
source .venv/bin/activate
python src/run_server.py
```

Expected local server URL:
- `http://0.0.0.0:8000/index.html`

Press `Ctrl+C` to stop.

## 7. Configure systemd Service

Create `/etc/systemd/system/urlgetloc.service`:

```ini
[Unit]
Description=urlgetloc mobile capture service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/urlgetloc
EnvironmentFile=/root/urlgetloc/.env
ExecStart=/root/urlgetloc/.venv/bin/python /root/urlgetloc/src/run_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable urlgetloc
sudo systemctl start urlgetloc
sudo systemctl status urlgetloc
```

## 8. Install and Configure Nginx

Install Nginx:

```bash
sudo apt update
sudo apt install -y nginx
```

Create Nginx config `/etc/nginx/sites-available/bbe.com`:

```nginx
server {
    listen 80;
    server_name bbe.com www.bbe.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /upload-json {
        client_max_body_size 20m;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/bbe.com /etc/nginx/sites-enabled/bbe.com
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Enable SSL (HTTPS)

Use Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d bbe.com -d www.bbe.com
```

After this, open:
- `https://bbe.com/index.html`

## 10. Telegram Integration Test

From VPS:

```bash
set -a
source .env
set +a
source .venv/bin/activate
python integrations/telegram_bot_sender.py
```

Expected:
- Telegram receives test message.

Then open page from phone and complete permission flow. On upload, Telegram summary should be sent automatically.

## 11. Troubleshooting

1. Service not running:
```bash
sudo journalctl -u urlgetloc -f
```

2. Nginx bad gateway:
- Check app service is running on `127.0.0.1:8000`.

3. Telegram not sending:
- Verify `TELEGRAM_NOTIFY_ENABLED=1`
- Verify token/chat id in `.env`
- Check service logs for `[TELEGRAM]` lines.

4. Camera/GPS blocked on phone:
- Use HTTPS URL
- Allow site permissions in mobile browser settings.
