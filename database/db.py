from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "database.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                target_spec TEXT NOT NULL,
                device_count INTEGER NOT NULL,
                finding_count INTEGER NOT NULL,
                risk_score INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                ip_address TEXT NOT NULL,
                vendor TEXT NOT NULL,
                model TEXT NOT NULL,
                firmware_version TEXT NOT NULL,
                services_json TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                FOREIGN KEY(report_id) REFERENCES reports(id)
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                device_ip TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                remediation TEXT NOT NULL,
                evidence TEXT NOT NULL,
                FOREIGN KEY(report_id) REFERENCES reports(id)
            );
            """
        )


def save_scan(target_spec, device_rows, findings, summary):
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO reports (created_at, target_spec, device_count, finding_count, risk_score, summary_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                target_spec,
                len(device_rows),
                len(findings),
                summary["risk_score"],
                json.dumps(summary),
            ),
        )
        report_id = cursor.lastrowid

        for device in device_rows:
            connection.execute(
                """
                INSERT INTO devices (
                    report_id, ip_address, vendor, model, firmware_version, services_json, risk_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    device["ip_address"],
                    device["vendor"],
                    device["model"],
                    device["firmware_version"],
                    json.dumps(device["services"]),
                    device["risk_score"],
                ),
            )

        for finding in findings:
            connection.execute(
                """
                INSERT INTO findings (
                    report_id, device_ip, severity, title, description, remediation, evidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    finding["device_ip"],
                    finding["severity"],
                    finding["title"],
                    finding["description"],
                    finding["remediation"],
                    finding["evidence"],
                ),
            )

        connection.commit()
        return report_id


def get_dashboard_stats():
    with get_connection() as connection:
        report_count = connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        device_count = connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        finding_count = connection.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        critical_count = connection.execute(
            "SELECT COUNT(*) FROM findings WHERE LOWER(severity) = 'critical'"
        ).fetchone()[0]

    return {
        "report_count": report_count,
        "device_count": device_count,
        "finding_count": finding_count,
        "critical_count": critical_count,
    }


def get_latest_report():
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 1").fetchone()
    return _build_report(row) if row else None


def get_report(report_id):
    if report_id is None:
        return None

    with get_connection() as connection:
        row = connection.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return _build_report(row) if row else None


def list_reports():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    return [_build_report(row, include_details=False) for row in rows]


def list_devices():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT d.*, r.created_at, r.target_spec
            FROM devices d
            JOIN reports r ON r.id = d.report_id
            ORDER BY d.id DESC
            """
        ).fetchall()

    devices = []
    for row in rows:
        devices.append(
            {
                "report_id": row["report_id"],
                "created_at": row["created_at"],
                "target_spec": row["target_spec"],
                "ip_address": row["ip_address"],
                "vendor": row["vendor"],
                "model": row["model"],
                "firmware_version": row["firmware_version"],
                "services": json.loads(row["services_json"]),
                "risk_score": row["risk_score"],
            }
        )
    return devices


def get_device_detail(report_id, ip_address):
    with get_connection() as connection:
        device_row = connection.execute(
            """
            SELECT d.*, r.created_at, r.target_spec, r.risk_score AS report_risk_score, r.summary_json
            FROM devices d
            JOIN reports r ON r.id = d.report_id
            WHERE d.report_id = ? AND d.ip_address = ?
            LIMIT 1
            """,
            (report_id, ip_address),
        ).fetchone()

        if device_row is None:
            return None

        finding_rows = connection.execute(
            """
            SELECT *
            FROM findings
            WHERE report_id = ? AND device_ip = ?
            ORDER BY id ASC
            """,
            (report_id, ip_address),
        ).fetchall()

    return {
        "report_id": device_row["report_id"],
        "created_at": device_row["created_at"],
        "target_spec": device_row["target_spec"],
        "report_risk_score": device_row["report_risk_score"],
        "ip_address": device_row["ip_address"],
        "vendor": device_row["vendor"],
        "model": device_row["model"],
        "firmware_version": device_row["firmware_version"],
        "services": json.loads(device_row["services_json"]),
        "risk_score": device_row["risk_score"],
        "summary": json.loads(device_row["summary_json"]),
        "findings": [
            {
                "severity": finding_row["severity"],
                "title": finding_row["title"],
                "description": finding_row["description"],
                "remediation": finding_row["remediation"],
                "evidence": finding_row["evidence"],
            }
            for finding_row in finding_rows
        ],
    }


def _build_report(row, include_details=True):
    if row is None:
        return None

    report = {
        "id": row["id"],
        "created_at": row["created_at"],
        "target_spec": row["target_spec"],
        "device_count": row["device_count"],
        "finding_count": row["finding_count"],
        "risk_score": row["risk_score"],
        "summary": json.loads(row["summary_json"]),
    }

    if not include_details:
        return report

    with get_connection() as connection:
        device_rows = connection.execute(
            "SELECT * FROM devices WHERE report_id = ? ORDER BY id ASC", (row["id"],)
        ).fetchall()
        finding_rows = connection.execute(
            "SELECT * FROM findings WHERE report_id = ? ORDER BY id ASC", (row["id"],)
        ).fetchall()

    report["devices"] = [
        {
            "ip_address": device_row["ip_address"],
            "vendor": device_row["vendor"],
            "model": device_row["model"],
            "firmware_version": device_row["firmware_version"],
            "services": json.loads(device_row["services_json"]),
            "risk_score": device_row["risk_score"],
        }
        for device_row in device_rows
    ]
    report["findings"] = [
        {
            "device_ip": finding_row["device_ip"],
            "severity": finding_row["severity"],
            "title": finding_row["title"],
            "description": finding_row["description"],
            "remediation": finding_row["remediation"],
            "evidence": finding_row["evidence"],
        }
        for finding_row in finding_rows
    ]
    return report
