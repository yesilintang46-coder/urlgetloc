import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

import cekfoto

# Validate HTML page exists
cekfoto._buat_halaman_kamera_mobile()
print("✓ HTML generated")

# Start server
port = cekfoto._start_server_mobile(directory=str(cekfoto.WEB_DIR), port=8020, use_https=False)
print(f"✓ Server started on port {port}")
time.sleep(0.5)

# Tiny test image (1x1 white PNG)
b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9gWf0AAAAASUVORK5CYII='
data_url = 'data:image/png;base64,' + b64

# Test GPS data
gps_test = {
    'latitude': -7.2505,
    'longitude': 112.7508,
    'accuracy': 8.5
}

# Upload
payload = json.dumps({
    'filename': 'test_gps.png',
    'dataUrl': data_url,
    'gps': gps_test
}).encode('utf-8')

req = Request(f'http://127.0.0.1:{port}/upload-json', 
              data=payload,
              headers={'Content-Type': 'application/json'},
              method='POST')

print(f"\nUploading test photo with GPS: {gps_test}")
try:
    with urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode('utf-8'))
        print(f"✓ Response: {body['message']}")
except Exception as e:
    print(f"✗ Error: {e}")

# Check saved files
time.sleep(0.5)
files = [
    p for p in cekfoto.PHONE_CAPTURES_DIR.glob('phone_*.*')
    if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
]
if files:
    latest = max(files, key=lambda p: p.stat().st_mtime)
    print(f"\n✓ Saved: {latest}")
    print(f"✓ Size: {latest.stat().st_size} bytes")
    
    # Check for GPS sidecar
    gps_json = latest.with_suffix('.gps.json')
    if gps_json.exists():
        print(f"✓ GPS backup JSON: {gps_json.read_text()}")

cekfoto._stop_server_mobile()
print("\n✓ Test completed")
