# Session 04 - Permission Lock Overlay

Date: 2026-09-09

## Goal
- Menambahkan flow agar user wajib grant kamera dan lokasi.
- Mengembalikan layout utama ke kartu gambar asli.
- Menyembunyikan kartu "permission required" lama.
- Menambahkan full-page lock overlay.
- Menandai lokasi kode lock-screen agar mudah dimodifikasi.

## Changes Implemented
- `web/index.html`:
  - Permission flow bergated (continue/retry + step status).
  - Overlay layar penuh ditambahkan untuk lock state.
  - Main image card tetap ditampilkan seperti semula.
  - Legacy permission card tetap ada tapi hidden.
  - Marker komentar `LOCK SCREEN ...` ditambahkan untuk lokasi edit cepat.

## Safety Note
- Browser permission tidak bisa dipaksa grant otomatis; flow dibuat sebagai hard-gate di level UI/app.
- Desain prompt dibuat sebagai in-app overlay, bukan meniru popup browser native.

## Validation
- `tests/test_gps_flow.py` tetap sukses setelah perubahan UI.
