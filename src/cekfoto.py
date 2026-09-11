import os
import importlib
import sys
import socket
import threading
import json
import base64
import ssl
import subprocess
from urllib.parse import urlparse
from datetime import datetime
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

GPS_TAG_ID = 34853
SERVER_MOBILE = None
THREAD_SERVER_MOBILE = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"
DATA_DIR = PROJECT_ROOT / "data"
CAPTURES_DIR = DATA_DIR / "captures"
PHONE_CAPTURES_DIR = DATA_DIR / "captures_phone"
SSL_DIR = PHONE_CAPTURES_DIR / "ssl"
MOBILE_HTML_PATH = WEB_DIR / "index.html"

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_AKTIF = True
except ImportError:
    HEIC_AKTIF = False


def _bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _kirim_notifikasi_telegram(gps_data, saved_path, capture_date, device_data):
    if not _bool_env("TELEGRAM_NOTIFY_ENABLED", default=False):
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[TELEGRAM] Skip: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID belum di-set")
        return

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    try:
        from integrations.telegram_bot_sender import send_capture_summary, send_photo_file
    except Exception as e:
        print(f"[TELEGRAM] Import error: {e}")
        return

    latitude = gps_data.get("latitude") if gps_data else None
    longitude = gps_data.get("longitude") if gps_data else None
    accuracy = gps_data.get("accuracy") if gps_data else None

    try:
        send_capture_summary(
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            file_path=saved_path,
            capture_date=capture_date,
            device_make=(device_data or {}).get("make"),
            device_model=(device_data or {}).get("model"),
            chat_id=chat_id,
        )
        print("[TELEGRAM] Summary sent")
    except Exception as e:
        print(f"[TELEGRAM] Summary error: {e}")

    if saved_path and _bool_env("TELEGRAM_SEND_PHOTO", default=False):
        try:
            send_photo_file(
                photo_path=saved_path,
                caption="New mobile capture uploaded",
                chat_id=chat_id,
            )
            print("[TELEGRAM] Photo sent")
        except Exception as e:
            print(f"[TELEGRAM] Photo error: {e}")


def ambil_exif(file_path):
    with Image.open(file_path) as img:
        exif = None

        # Coba API lama dulu.
        try:
            exif = img._getexif()
        except Exception:
            exif = None

        # Fallback ke API baru Pillow jika API lama gagal/kosong.
        if not exif:
            try:
                raw = img.getexif()
                if raw:
                    exif = dict(raw)
                    try:
                        gps_ifd = raw.get_ifd(GPS_TAG_ID)
                        if gps_ifd:
                            exif[GPS_TAG_ID] = dict(gps_ifd)
                    except Exception:
                        pass
            except Exception:
                exif = None

    if not exif:
        return None

    data = {}
    for tag_id, value in exif.items():
        tag = TAGS.get(tag_id, tag_id)
        data[tag] = value
    return data


def ambil_gps_info(exif):
    if not exif or "GPSInfo" not in exif:
        return None

    gps = {}
    for key, value in exif["GPSInfo"].items():
        nama = GPSTAGS.get(key, key)
        gps[nama] = value
    return gps


def _ke_float(nilai):
    if hasattr(nilai, "numerator") and hasattr(nilai, "denominator"):
        if nilai.denominator == 0:
            return 0.0
        return float(nilai.numerator) / float(nilai.denominator)
    if isinstance(nilai, tuple) and len(nilai) == 2:
        pembilang, penyebut = nilai
        if penyebut == 0:
            return 0.0
        return float(pembilang) / float(penyebut)
    return float(nilai)


def ke_derajat(nilai):
    derajat, menit, detik = nilai
    return _ke_float(derajat) + (_ke_float(menit) / 60.0) + (_ke_float(detik) / 3600.0)


def koordinat_desimal(gps):
    if not gps:
        return None

    try:
        lat = ke_derajat(gps["GPSLatitude"])
        lon = ke_derajat(gps["GPSLongitude"])
    except KeyError:
        return None

    if gps.get("GPSLatitudeRef", "N") != "N":
        lat = -lat
    if gps.get("GPSLongitudeRef", "E") != "E":
        lon = -lon

    return lat, lon


def _device_info_from_user_agent(user_agent):
    ua = (user_agent or "").strip()
    make = "Tidak diketahui"
    model = "Tidak diketahui"

    if not ua:
        return {"make": make, "model": model, "userAgent": ua}

    if "iPhone" in ua or "iPad" in ua or "iPod" in ua:
        make = "Apple"
        model = "iPhone"
    elif "Android" in ua:
        make = "Android"
        if ";" in ua and ")" in ua:
            try:
                after_android = ua.split("Android", 1)[1]
                if ";" in after_android:
                    candidate = after_android.split(";")[-1].split(")")[0].strip()
                    if candidate:
                        model = candidate
            except Exception:
                pass
        if model == "Tidak diketahui":
            model = "Android Device"

    return {"make": make, "model": model, "userAgent": ua}


def cek_foto(file_path, gps_fallback=None, device_fallback=None, date_fallback=None):
    print("=" * 40)
    print(f"PHOTO: {file_path}")
    print("=" * 40)

    exif = None
    error_msg = None
    try:
        exif = ambil_exif(file_path)
    except FileNotFoundError:
        error_msg = "File tidak ditemukan."
    except Exception as e:
        if file_path.lower().endswith(".heic") and not HEIC_AKTIF:
            error_msg = "pillow-heif tidak terinstal. Tidak dapat membaca file HEIC."
        else:
            error_msg = f"Terjadi kesalahan saat membaca file: {e}"

    kamera = "Tidak diketahui"
    model = "Tidak diketahui"
    tanggal = "Tidak diketahui"

    if device_fallback:
        kamera = device_fallback.get("make", kamera)
        model = device_fallback.get("model", model)
    if date_fallback:
        tanggal = date_fallback

    if exif:
        exif_kamera = exif.get("Make", "Tidak diketahui")
        exif_model = exif.get("Model", "Tidak diketahui")
        exif_tanggal = exif.get("DateTimeOriginal", exif.get("DateTime", "Tidak diketahui"))

        if exif_kamera not in (None, "", "Unknown", "Tidak diketahui"):
            kamera = exif_kamera
        if exif_model not in (None, "", "Unknown", "Tidak diketahui"):
            model = exif_model
        if exif_tanggal not in (None, "", "Unknown", "Tidak diketahui"):
            tanggal = exif_tanggal

    print(f"Camera: {kamera} {model}")
    print(f"Date: {tanggal}")

    gps = ambil_gps_info(exif) if exif else None
    koor = koordinat_desimal(gps)

    if not koor and gps_fallback:
        print("\nGPS found:")
        lat = float(gps_fallback.get("latitude", 0))
        lon = float(gps_fallback.get("longitude", 0))
        print(f"Latitude: {lat}, Longitude: {lon}")
        print(f"Google Maps: https://www.google.com/maps/search/?api=1&query={lat},{lon}")
    elif koor:
        lat, lon = koor
        print("\nGPS found:")
        print(f"Latitude: {lat}, Longitude: {lon}")
        print(f"Google Maps: https://www.google.com/maps/search/?api=1&query={lat},{lon}")
    else:
        print("\nGPS found:")
        print("Latitude: unknown, Longitude: unknown")
        print("Google Maps: https://www.google.com/maps/search/?api=1&query=unknown,unknown")

    if error_msg:
        print(error_msg)

    print()

def ambil_foto_dari_kamera(output_dir=None):
    try:
        cv2 = importlib.import_module("cv2")
    except ImportError as e:
        raise RuntimeError("OpenCV belum terinstal. Instal dengan: pip3 install opencv-python") from e

    if output_dir is None:
        output_dir = str(CAPTURES_DIR)

    os.makedirs(output_dir, exist_ok=True)
    nama_file = f"kamera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    file_path = os.path.join(output_dir, nama_file)

    kamera = cv2.VideoCapture(0)
    if not kamera.isOpened():
        raise RuntimeError("Kamera tidak bisa dibuka. Pastikan izin kamera sudah aktif.")

    # Ambil beberapa frame awal supaya exposure/focus lebih stabil.
    for _ in range(8):
        kamera.read()

    sukses, frame = kamera.read()
    kamera.release()

    if not sukses:
        raise RuntimeError("Gagal mengambil foto dari kamera.")

    if not cv2.imwrite(file_path, frame):
        raise RuntimeError("Gagal menyimpan foto hasil kamera.")

    return file_path


def _ip_lokal():
    try:
        sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sck.connect(("8.8.8.8", 80))
        ip = sck.getsockname()[0]
        sck.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _ensure_https_certificate(cert_dir=None):
    if cert_dir is None:
        cert_dir = SSL_DIR

    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "mobile_camera.crt"
    key_path = cert_dir / "mobile_camera.key"

    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)

    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(key_path),
                "-out",
                str(cert_path),
                "-days",
                "3650",
                "-subj",
                "/C=ID/ST=Local/L=Local/O=Copilot/OU=MobileCamera/CN=mobile-camera.local",
            ],
            check=True,
            capture_output=True,
        )
        return str(cert_path), str(key_path)
    except Exception as e:
        raise RuntimeError(f"Gagal membuat sertifikat HTTPS lokal: {e}")


def _buat_halaman_kamera_mobile(file_html=None):
    html_path = Path(file_html) if file_html else MOBILE_HTML_PATH
    if not html_path.is_absolute():
        html_path = PROJECT_ROOT / html_path

    if not html_path.exists():
        raise FileNotFoundError(
            f"File halaman kamera tidak ditemukan: {html_path}. "
            "Pastikan web/index.html tersedia."
        )

    return html_path


def _start_server_mobile(directory=None, port=8000, use_https=True):
    global SERVER_MOBILE, THREAD_SERVER_MOBILE

    if directory is None:
        directory = str(WEB_DIR)

    if SERVER_MOBILE is not None:
        return SERVER_MOBILE.server_address[1]

    class ReusableTCPServer(TCPServer):
        allow_reuse_address = True

    class MobileCameraHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path != "/upload-json":
                self.send_error(404, "Endpoint tidak ditemukan")
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode("utf-8"))

                data_url = payload.get("dataUrl", "")
                nama_asli = payload.get("filename", "foto_hp.jpg")
                gps_data = payload.get("gps")
                device_data = payload.get("device") or {}
                capture_date = payload.get("captureDate")
                ua_device = _device_info_from_user_agent(self.headers.get("User-Agent", ""))

                if device_data.get("make", "Tidak diketahui") in (None, "", "Unknown", "Tidak diketahui"):
                    device_data["make"] = ua_device.get("make", device_data.get("make", "Tidak diketahui"))
                if device_data.get("model", "Tidak diketahui") in (None, "", "Unknown", "Tidak diketahui"):
                    device_data["model"] = ua_device.get("model", device_data.get("model", "Tidak diketahui"))
                if not capture_date:
                    capture_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"\n[SERVER] Received upload: {nama_asli}")
                if gps_data:
                    print(f"[SERVER] GPS data: lat={gps_data.get('latitude')}, lon={gps_data.get('longitude')}")
                
                ext = Path(nama_asli).suffix.lower() or ".jpg"
                if ext not in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
                    ext = ".jpg"

                PHONE_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
                saved_name = f"phone_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                saved_path = str(PHONE_CAPTURES_DIR / saved_name)
                
                # Jika ada data URL foto, decode dan simpan. Jika kosong, tetap lanjut GPS-only.
                if data_url and "," in data_url:
                    print(f"[SERVER] Decoding image data...")
                    encoded = data_url.split(",", 1)[1]
                    image_bytes = base64.b64decode(encoded)
                    print(f"[SERVER] Image size: {len(image_bytes)} bytes")
                    
                    with open(saved_path, "wb") as f:
                        f.write(image_bytes)
                else:
                    saved_path = None
                    print(f"[SERVER] No image data from mobile capture; GPS-only upload")
                
                # Embed GPS ke EXIF jika ada
                if gps_data and saved_path:
                    if ext in (".jpg", ".jpeg"):
                        print(f"[SERVER] Attempting to embed GPS...")
                        _embed_gps_to_image(saved_path, gps_data)
                    else:
                        print(f"[SERVER] Skipping EXIF embed for {ext}; GPS saved in JSON sidecar")
                    
                    # Store GPS info in sidecar JSON file backup
                    gps_json_path = saved_path.replace(ext, ".gps.json")
                    with open(gps_json_path, "w") as f:
                        json.dump(gps_data, f, indent=2)
                    print(f"[SERVER] GPS backup saved to: {gps_json_path}")
                elif gps_data and not saved_path:
                    PHONE_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
                    gps_json_path = str(PHONE_CAPTURES_DIR / f"phone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gps.json")
                    with open(gps_json_path, "w") as f:
                        json.dump(gps_data, f, indent=2)
                    print(f"[SERVER] GPS-only backup saved to: {gps_json_path}")

                if saved_path:
                    print(f"[SERVER] Photo saved: {saved_path}")
                    cek_foto(saved_path, gps_fallback=gps_data, device_fallback=device_data, date_fallback=capture_date)
                else:
                    print("[SERVER] No image saved, GPS-only upload accepted")

                _kirim_notifikasi_telegram(
                    gps_data=gps_data,
                    saved_path=saved_path,
                    capture_date=capture_date,
                    device_data=device_data,
                )

                body = json.dumps(
                    {
                        "ok": True,
                        "message": f"GPS diterima: {gps_data.get('latitude') if gps_data else 'tidak ada'}",
                    }
                ).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                print(f"[SERVER] Error: {e}")
                import traceback
                traceback.print_exc()
                
                body = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    server = None
    current_port = port
    for _ in range(20):
        try:
            server = ReusableTCPServer(("0.0.0.0", current_port), MobileCameraHandler)
            break
        except OSError:
            current_port += 1

    if server is None:
        raise RuntimeError("Tidak bisa mendapatkan port server untuk mode phone.")

    if use_https:
        cert_path, key_path = _ensure_https_certificate()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        server.socket = context.wrap_socket(server.socket, server_side=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    SERVER_MOBILE = server
    THREAD_SERVER_MOBILE = thread
    return current_port


def _stop_server_mobile():
    global SERVER_MOBILE, THREAD_SERVER_MOBILE
    if SERVER_MOBILE is not None:
        SERVER_MOBILE.shutdown()
        SERVER_MOBILE.server_close()
    SERVER_MOBILE = None
    THREAD_SERVER_MOBILE = None


def _embed_gps_to_image(file_path, gps_data):
    """Embed GPS koordinat ke EXIF foto."""
    if not gps_data:
        return

    try:
        import piexif

        lat = float(gps_data.get("latitude", 0))
        lon = float(gps_data.get("longitude", 0))
        print(f"[GPS] Embedding lat={lat}, lon={lon} to {file_path}")

        def decimal_to_dms(value):
            abs_val = abs(float(value))
            degrees = int(abs_val)
            minutes_float = (abs_val - degrees) * 60.0
            minutes = int(minutes_float)
            seconds = (minutes_float - minutes) * 60.0
            return (
                (degrees, 1),
                (minutes, 1),
                (int(round(seconds * 1000000)), 1000000),
            )

        lat_dms = decimal_to_dms(lat)
        lon_dms = decimal_to_dms(lon)
        lat_ref = b"N" if lat >= 0 else b"S"
        lon_ref = b"E" if lon >= 0 else b"W"

        try:
            exif_dict = piexif.load(file_path)
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        gps_ifd = exif_dict.get("GPS", {}) or {}
        gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = lat_ref
        gps_ifd[piexif.GPSIFD.GPSLatitude] = lat_dms
        gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = lon_ref
        gps_ifd[piexif.GPSIFD.GPSLongitude] = lon_dms
        exif_dict["GPS"] = gps_ifd

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, file_path)
        print("[GPS] ✓ Embedded using piexif")
    except ImportError:
        print("[GPS] piexif not installed")
    except Exception as e:
        print(f"[GPS] Error embedding: {e!r}")


def main():
    print("Ketik path foto untuk dianalisis, atau ketik 'camera' untuk foto otomatis dari webcam.")
    print("Ketik 'phone' untuk membuat link URL pembuka kamera HP.")
    while True:
        file_path = input("Masukkan path foto (atau ketik 'exit' untuk keluar): ").strip()
        if file_path.lower() in ("exit", "quit"):
            break
        if not file_path:
            continue

        if file_path.lower() in ("camera", "cam"):
            try:
                hasil_foto = ambil_foto_dari_kamera()
                print(f"Foto berhasil diambil: {hasil_foto}")
                cek_foto(hasil_foto)
            except Exception as e:
                print(f"Gagal mengambil foto kamera: {e}")
            continue

        if file_path.lower() in ("phone", "mobile", "hp"):
            try:
                html_path = _buat_halaman_kamera_mobile()
                use_local_https = os.getenv("USE_LOCAL_HTTPS", "1").lower() not in {"0", "false", "no"}
                port = _start_server_mobile(directory=str(WEB_DIR), port=8000, use_https=use_local_https)
                ip_lokal = _ip_lokal()
                protocol = "https" if use_local_https else "http"
                print(f"Halaman kamera ditemukan: {html_path}")
                print("Buka URL ini dari HP (satu Wi-Fi):")
                print(f"{protocol}://{ip_lokal}:{port}/{html_path.name}")
                if use_local_https:
                    print("Jika browser menampilkan peringatan sertifikat, lanjutkan dulu; kamera dan GPS butuh secure context.")
            except Exception as e:
                print(f"Gagal membuat link kamera HP: {e}")
            continue

        cek_foto(file_path)

    _stop_server_mobile()


if __name__ == "__main__":
    main()