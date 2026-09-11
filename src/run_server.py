import os
import time

import cekfoto


def main():
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    use_local_https = cekfoto._bool_env("USE_LOCAL_HTTPS", default=False)

    html_path = cekfoto._buat_halaman_kamera_mobile()
    running_port = cekfoto._start_server_mobile(
        directory=str(cekfoto.WEB_DIR),
        port=port,
        use_https=use_local_https,
    )

    protocol = "https" if use_local_https else "http"
    print(f"[SERVER] Started {protocol}://{host}:{running_port}/{html_path.name}")
    print("[SERVER] Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SERVER] Stopping...")
    finally:
        cekfoto._stop_server_mobile()


if __name__ == "__main__":
    main()
