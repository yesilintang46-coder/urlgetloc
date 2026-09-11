# Session 03 - UI Bootstrap, Rename, Guidebook

Date: 2026-09-05 to 2026-09-09

## Goal
- Jadikan tampilan HTML mudah diubah tanpa merusak logic.
- Sembunyikan layout lama, tampilkan satu Bootstrap card saja.
- Ubah nama `mobile_camera.html` menjadi `index.html`.
- Buat guidebook lengkap.

## Changes Implemented
- Refactor `web/index.html`:
  - area config editable dipisah dari core logic
  - tampilan visible menjadi 1 Bootstrap card
  - status memakai class alert Bootstrap
- Rename file:
  - `web/mobile_camera.html` -> `web/index.html`
- Update referensi:
  - `src/cekfoto.py`
  - `docs/HOSTING.md`
  - helper script di `scripts/`
- Guidebook dibuat:
  - `docs/GUIDEBOOK.md`

## Validation
- Test upload flow tetap sukses setelah perubahan UI dan rename file.

## Final State
- App lokal berjalan normal.
- Struktur project rapi.
- Hosting + konfigurasi Telegram sudah terdokumentasi.
