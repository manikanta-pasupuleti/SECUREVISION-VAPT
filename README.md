# SecureVision VAPT

SecureVision VAPT is a defensive assessment dashboard for CCTV cameras and DVRs. It accepts an IP range or device list, simulates safe discovery and fingerprinting, checks for common surveillance-device weaknesses, scores the risk, and stores the results in a local SQLite database for review.

## Run

```bash
pip install -r requirements.txt
python app.py
```

Then open the local Flask URL shown in the terminal.

## What it includes

- Device discovery from CIDR blocks or comma-separated IP lists
- Firmware and service fingerprinting
- Safe vulnerability simulation for Telnet, RTSP, ONVIF, and outdated firmware baselines
- Persisted report history and device inventory
- Interactive dashboard pages for findings and remediation tracking
