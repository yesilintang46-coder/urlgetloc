from pathlib import Path
import re

path = Path('/Users/iktidptsi/Downloads/cekfoto.py')
text = path.read_text()

cek_foto_new = '''def cek_foto(file_path, gps_fallback=None):
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

    if exif:
        kamera = exif.get("Make", "Tidak diketahui")
        model = exif.get("Model", "Tidak diketahui")
        tanggal = exif.get("DateTimeOriginal", exif.get("DateTime", "Tidak diketahui"))
        print(f"Camera: {kamera} {model}")
        print(f"Date: {tanggal}")
    else:
        print("Camera: Tidak diketahui Tidak diketahui")
        print("Date: Tidak diketahui")

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
'''

embed_new = '''def _embed_gps_to_image(file_path, gps_data):
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
        print(f"[GPS] Error embedding: {e}")
'''

text, count1 = re.subn(r'def cek_foto\(file_path, gps_fallback=None\):.*?\n(?=def ambil_foto_dari_kamera\()' , cek_foto_new + '\n', text, flags=re.S)
if count1 != 1:
    raise SystemExit(f'cek_foto replace failed: {count1}')

text, count2 = re.subn(r'def _embed_gps_to_image\(file_path, gps_data\):.*?\n(?=def main\()' , embed_new + '\n', text, flags=re.S)
if count2 != 1:
    raise SystemExit(f'embed replace failed: {count2}')

path.write_text(text)
print('patched')
