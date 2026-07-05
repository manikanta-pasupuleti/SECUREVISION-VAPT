# SecureVision VAPT

SecureVision VAPT is a defensive assessment dashboard for CCTV cameras and DVRs. It accepts an IP range or device list, simulates safe discovery and fingerprinting, checks for common surveillance-device weaknesses, scores the risk, and stores the results in a local SQLite database for review.

## Run

```bash
pip install -r requirements.txt
python app.py
```

Then open the local Flask URL shown in the terminal.

## Live deploy on Oracle VM

Use `wsgi.py` with `gunicorn` for production:

```bash
export SECRET_KEY='change-me'
export FLASK_DEBUG=0
export HOST=0.0.0.0
export PORT=8000
gunicorn -b 127.0.0.1:8000 wsgi:app
```

Optionally set `SECUREVISION_DB_PATH` to move the SQLite database outside the repo directory.

## What it includes

- Device discovery from CIDR blocks or comma-separated IP lists
- Firmware and service fingerprinting
- Safe vulnerability simulation for Telnet, RTSP, ONVIF, and outdated firmware baselines
- Persisted report history and device inventory
- Interactive dashboard pages for findings and remediation tracking

## Repository hygiene

The project ignores generated and local-only artifacts such as Python bytecode, virtual environments, backups, and the local SQLite database. Those files should stay untracked so a fresh clone remains clean and portable.
