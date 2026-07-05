from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from database.db import (
    get_dashboard_stats,
    get_device_detail,
    get_latest_report,
    get_report,
    init_db,
    list_devices,
    list_reports,
    save_scan,
)
from scanner.discovery import discover_devices
from scanner.fingerprint import fingerprint_device
from scanner.report import generate_report
from scanner.risk_score import calculate_risk_score
from scanner.vulnerability import scan_vulnerabilities
from utils.helpers import parse_target_input
from utils.logger import get_logger, setup_logging


BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["SECRET_KEY"] = "securevision-vapt-demo"


setup_logging()
logger = get_logger(__name__)
init_db()


def run_scan(target_spec: str, mode: str = "simulated"):
    targets = parse_target_input(target_spec)
    discovered = discover_devices(targets, mode=mode)

    device_rows = []
    findings = []

    for device in discovered:
        fingerprinted = fingerprint_device(device)
        device_findings = scan_vulnerabilities(fingerprinted)
        risk_score = calculate_risk_score(device_findings)

        device_rows.append({**fingerprinted, "risk_score": risk_score})
        findings.extend(device_findings)

    summary = generate_report(device_rows, findings)
    report_id = save_scan(target_spec, device_rows, findings, summary)
    return report_id


@app.route("/")
def index():
    stats = get_dashboard_stats()
    latest_report = get_latest_report()
    return render_template("index.html", stats=stats, latest_report=latest_report)


@app.route("/scan", methods=["POST"])
def scan():
    target_spec = request.form.get("targets", "").strip()
    live_flag = request.form.get("live")
    mode = "live" if live_flag else "simulated"
    if not target_spec:
        flash("Provide at least one IP address, CIDR block, or comma-separated device list.", "error")
        return redirect(url_for("index"))

    try:
        report_id = run_scan(target_spec, mode=mode)
        flash("Scan completed and stored in the report history.", "success")
        return redirect(url_for("dashboard", report_id=report_id))
    except ValueError as exc:
        logger.exception("Scan failed")
        flash(str(exc), "error")
        return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    report_id = request.args.get("report_id", type=int)
    report = get_report(report_id) if report_id else get_latest_report()
    stats = get_dashboard_stats()
    return render_template("dashboard.html", report=report, stats=stats)


@app.route("/devices")
def devices():
    return render_template("devices.html", devices=list_devices(), stats=get_dashboard_stats())


@app.route("/devices/<int:report_id>/<path:ip_address>")
def device_detail(report_id, ip_address):
    device = get_device_detail(report_id, ip_address)
    if device is None:
        flash("Device not found for the selected report.", "error")
        return redirect(url_for("devices"))

    return render_template("device_detail.html", device=device, stats=get_dashboard_stats())


@app.route("/reports")
def reports():
    return render_template("reports.html", reports=list_reports(), stats=get_dashboard_stats())


if __name__ == "__main__":
    app.run(debug=True)
