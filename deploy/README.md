# Deploy Templates

This folder contains ready-to-use deployment templates for Hostinger VPS.

## Files

- `systemd/urlgetloc.service`
- `nginx/bbe.com.conf`

## 1) Prepare systemd service

Open `systemd/urlgetloc.service` and replace:

- `__APP_USER__` -> your VPS Linux username
- `__APP_DIR__` -> absolute project path in VPS

Example:

- `User=ubuntu`
- `WorkingDirectory=/home/ubuntu/urlgetloc`
- `EnvironmentFile=/home/ubuntu/urlgetloc/.env`
- `ExecStart=/home/ubuntu/urlgetloc/.venv/bin/python /home/ubuntu/urlgetloc/src/run_server.py`

Install and start service:

```bash
sudo cp deploy/systemd/urlgetloc.service /etc/systemd/system/urlgetloc.service
sudo systemctl daemon-reload
sudo systemctl enable urlgetloc
sudo systemctl start urlgetloc
sudo systemctl status urlgetloc
```

## 2) Prepare Nginx for bbe.com

Install and enable config:

```bash
sudo cp deploy/nginx/bbe.com.conf /etc/nginx/sites-available/bbe.com
sudo ln -s /etc/nginx/sites-available/bbe.com /etc/nginx/sites-enabled/bbe.com
sudo nginx -t
sudo systemctl reload nginx
```

## 3) Enable HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d bbe.com -d www.bbe.com
```

## 4) Telegram env configuration

Set in `.env`:

```env
TELEGRAM_NOTIFY_ENABLED=1
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID
TELEGRAM_SEND_PHOTO=0
```

App env basics:

```env
APP_HOST=0.0.0.0
APP_PORT=8000
USE_LOCAL_HTTPS=0
```
