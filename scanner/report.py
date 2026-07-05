from __future__ import annotations


def generate_report(device_rows, findings):
    risk_score = min(100, sum(device["risk_score"] for device in device_rows))

    severity_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        severity = finding["severity"].lower()
        if severity in severity_breakdown:
            severity_breakdown[severity] += 1

    prioritized_findings = sorted(
        findings,
        key=lambda finding: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(finding["severity"].lower(), 4),
    )

    return {
        "risk_score": risk_score,
        "severity_breakdown": severity_breakdown,
        "prioritized_findings": prioritized_findings,
        "device_total": len(device_rows),
        "finding_total": len(findings),
        "remediation_priority": [
            "Remove default credentials from all exposed devices.",
            "Close Telnet and restrict management services to trusted subnets.",
            "Upgrade firmware and validate vendor advisories before re-exposure.",
        ],
    }
