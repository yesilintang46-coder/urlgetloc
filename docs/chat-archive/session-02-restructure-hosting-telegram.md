# Session 02 - Restructure, Hosting, Telegram

Date: 2026-09-05

## Goal
- Rapikan struktur project.
- Perbaiki halaman mobile camera agar mudah dimodifikasi.
- Tambah panduan hosting.
- Siapkan integrasi Telegram bot untuk tahap hosted.

## Changes Implemented
- Struktur folder dibersihkan:
  - `src/`, `web/`, `tests/`, `scripts/`, `data/`, `docs/`, `integrations/`
- File utama dipindahkan:
  - `src/cekfoto.py`
  - `web/mobile_camera.html` (kemudian di sesi berikutnya diubah menjadi `web/index.html`)
  - `tests/test_gps_flow.py`
- Perbaikan path handling di `src/cekfoto.py`:
  - konstanta root/path terpusat
  - mode hosting via env `USE_LOCAL_HTTPS=0`
- Dokumentasi hosting dibuat:
  - `docs/HOSTING.md`
- Modul Telegram dibuat:
  - `integrations/telegram_bot_sender.py`

## Validation
- Test flow dijalankan beberapa kali dengan hasil sukses (`ok: true`).

## Notes
- EXIF embed dilewati untuk file non-JPEG; GPS tetap disimpan ke sidecar JSON.
