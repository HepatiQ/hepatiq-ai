#!/usr/bin/env python3
"""Fail CI on HIGH or CRITICAL dependency advisories.

``pip-audit`` reports advisory IDs and fix versions, but not severity. This
wrapper runs ``pip-audit``, resolves each advisory through the OSV API, and
enforces the project threshold:

* CRITICAL and HIGH fail the build.
* MEDIUM and LOW are reported but do not fail the build.
* Unknown severity fails closed so an advisory cannot be silently ignored.

Usage:
    python scripts/dependency_audit.py
    python scripts/dependency_audit.py --audit-json pip-audit.json
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQUIREMENTS = ROOT / "requirements.txt"
DEFAULT_OSV_URL = "https://api.osv.dev/v1/vulns/{vuln_id}"
FAILING_SEVERITIES = {"HIGH", "CRITICAL", "UNKNOWN"}
SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4, "UNKNOWN": 5}


@dataclass(frozen=True)
class Finding:
    package: str
    version: str
    vuln_id: str
    severity: str
    fix_versions: tuple[str, ...]


def run_pip_audit(requirements: Path) -> dict[str, Any]:
    """Run pip-audit and return its JSON output.

    pip-audit exits with code 1 when it finds vulnerabilities; that is an
    expected result because this wrapper applies the severity threshold.
    """

    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "-r",
        str(requirements),
        "--format",
        "json",
        "--vulnerability-service",
        "osv",
        "--progress-spinner",
        "off",
    ]
    completed = subprocess.run(command, capture_output=True, encoding="utf-8", text=True, check=False)
    if completed.returncode not in (0, 1):
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"pip-audit failed with exit code {completed.returncode}: {detail}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("pip-audit did not return valid JSON") from exc


def _roundup(value: float) -> float:
    return math.ceil((value * 10) - 1e-9) / 10


def _cvss_metric(metrics: dict[str, str], name: str) -> str:
    try:
        return metrics[name]
    except KeyError as exc:
        raise ValueError(f"missing CVSS metric {name}") from exc


def cvss_v3_base_score(vector: str) -> float | None:
    """Return the CVSS v3 base score for a vector, or None when unsupported."""

    try:
        metrics = dict(part.split(":", 1) for part in vector.split("/")[1:])
        attack_vector = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}[_cvss_metric(metrics, "AV")]
        attack_complexity = {"L": 0.77, "H": 0.44}[_cvss_metric(metrics, "AC")]
        scope_changed = _cvss_metric(metrics, "S") == "C"
        privileges_required = {
            "N": 0.85,
            "L": 0.68 if scope_changed else 0.62,
            "H": 0.5 if scope_changed else 0.27,
        }[_cvss_metric(metrics, "PR")]
        user_interaction = {"N": 0.85, "R": 0.62}[_cvss_metric(metrics, "UI")]
        confidentiality = {"H": 0.56, "L": 0.22, "N": 0.0}[_cvss_metric(metrics, "C")]
        integrity = {"H": 0.56, "L": 0.22, "N": 0.0}[_cvss_metric(metrics, "I")]
        availability = {"H": 0.56, "L": 0.22, "N": 0.0}[_cvss_metric(metrics, "A")]
    except (KeyError, ValueError):
        return None

    iss = 1 - (1 - confidentiality) * (1 - integrity) * (1 - availability)
    if scope_changed:
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    else:
        impact = 6.42 * iss
    exploitability = 8.22 * attack_vector * attack_complexity * privileges_required * user_interaction
    if impact <= 0:
        return 0.0
    if scope_changed:
        return _roundup(min(1.08 * (impact + exploitability), 10.0))
    return _roundup(min(impact + exploitability, 10.0))


def score_to_severity(score: float) -> str:
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "UNKNOWN"


def normalise_severity(value: str | None) -> str | None:
    if not value:
        return None
    normalised = value.strip().upper()
    if normalised == "MODERATE":
        return "MEDIUM"
    if normalised in SEVERITY_RANK:
        return normalised
    return None


def _severity_from_osv_document(document: dict[str, Any]) -> str | None:
    database_specific = document.get("database_specific")
    if isinstance(database_specific, dict):
        severity = normalise_severity(database_specific.get("severity"))
        if severity:
            return severity

    scores = []
    for item in document.get("severity", []):
        if not isinstance(item, dict):
            continue
        raw_score = item.get("score")
        if not isinstance(raw_score, str):
            continue
        if raw_score.startswith("CVSS:3."):
            base_score = cvss_v3_base_score(raw_score)
            if base_score is not None:
                scores.append(base_score)
    if scores:
        return score_to_severity(max(scores))

    for affected in document.get("affected", []):
        if not isinstance(affected, dict):
            continue
        affected_specific = affected.get("database_specific")
        if isinstance(affected_specific, dict):
            severity = normalise_severity(affected_specific.get("severity"))
            if severity:
                return severity
    return None


def fetch_osv_document(vuln_id: str, *, template: str, timeout: float) -> dict[str, Any] | None:
    url = template.format(vuln_id=urllib.parse.quote(vuln_id, safe=""))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except OSError as exc:
        raise RuntimeError(f"OSV lookup failed for {vuln_id}: {exc}") from exc


def lookup_severity(
    vulnerability: dict[str, Any],
    *,
    fetch: Callable[[str], dict[str, Any] | None],
) -> str:
    identifiers = [vulnerability.get("id"), *(vulnerability.get("aliases") or [])]
    severities = []
    for identifier in identifiers:
        if not isinstance(identifier, str) or not identifier:
            continue
        document = fetch(identifier)
        if document is None:
            continue
        severity = _severity_from_osv_document(document)
        if severity:
            severities.append(severity)
    if not severities:
        return "UNKNOWN"
    return max(severities, key=lambda severity: SEVERITY_RANK[severity])


def collect_findings(
    audit: dict[str, Any],
    *,
    severity_lookup: Callable[[dict[str, Any]], str],
) -> list[Finding]:
    findings = []
    for dependency in audit.get("dependencies") or []:
        if not isinstance(dependency, dict):
            continue
        package = str(dependency.get("name", "unknown"))
        version = str(dependency.get("version", "unknown"))
        for vulnerability in dependency.get("vulns") or []:
            if not isinstance(vulnerability, dict):
                continue
            vuln_id = str(vulnerability.get("id", "unknown"))
            fixes = vulnerability.get("fix_versions") or []
            findings.append(
                Finding(
                    package=package,
                    version=version,
                    vuln_id=vuln_id,
                    severity=severity_lookup(vulnerability),
                    fix_versions=tuple(str(fix) for fix in fixes),
                )
            )
    return findings


def report(findings: list[Finding]) -> int:
    if not findings:
        print("No known vulnerabilities found.")
        return 0

    print(f"Found {len(findings)} known vulnerability record(s).")
    for finding in sorted(findings, key=lambda item: (-SEVERITY_RANK[item.severity], item.package, item.vuln_id)):
        fixes = ", ".join(finding.fix_versions) if finding.fix_versions else "none published"
        print(f"  {finding.severity:<8} {finding.package}=={finding.version} {finding.vuln_id} (fix: {fixes})")
        print(f"           https://osv.dev/vulnerability/{finding.vuln_id}")

    failures = [finding for finding in findings if finding.severity in FAILING_SEVERITIES]
    if failures:
        print(
            f"FAIL: {len(failures)} advisory/advisories meet the HIGH/CRITICAL "
            "threshold or have unknown severity."
        )
        return 1
    print("PASS: only LOW/MEDIUM advisories found; threshold is HIGH/CRITICAL.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--audit-json", type=Path, help="Use an existing pip-audit JSON report.")
    parser.add_argument("--osv-url", default=DEFAULT_OSV_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)

    if args.audit_json:
        audit = json.loads(args.audit_json.read_text(encoding="utf-8"))
    else:
        audit = run_pip_audit(args.requirements)

    cache: dict[str, dict[str, Any] | None] = {}

    def fetch(vuln_id: str) -> dict[str, Any] | None:
        if vuln_id not in cache:
            cache[vuln_id] = fetch_osv_document(vuln_id, template=args.osv_url, timeout=args.timeout)
        return cache[vuln_id]

    findings = collect_findings(
        audit,
        severity_lookup=lambda vulnerability: lookup_severity(vulnerability, fetch=fetch),
    )
    return report(findings)


if __name__ == "__main__":
    raise SystemExit(main())
