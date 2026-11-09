"""Regression tests for the CI dependency severity gate."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dependency_audit", ROOT / "scripts" / "dependency_audit.py")
assert SPEC is not None and SPEC.loader is not None
dependency_audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = dependency_audit
SPEC.loader.exec_module(dependency_audit)

Finding = dependency_audit.Finding


def test_cvss_v3_base_score_matches_published_examples():
    assert dependency_audit.cvss_v3_base_score(
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    ) == 9.8
    assert dependency_audit.cvss_v3_base_score(
        "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H"
    ) == 6.5


def test_osv_database_severity_wins_over_vector():
    document = {
        "database_specific": {"severity": "HIGH"},
        "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H"}],
    }

    assert dependency_audit._severity_from_osv_document(document) == "HIGH"


def test_cvss_v3_vectors_are_classified():
    document = {
        "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}]
    }

    assert dependency_audit._severity_from_osv_document(document) == "CRITICAL"


def test_unsupported_cvss_v4_without_database_severity_is_unknown():
    document = {
        "severity": [
            {
                "type": "CVSS_V4",
                "score": "CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:P/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
            }
        ]
    }

    assert dependency_audit._severity_from_osv_document(document) is None


def test_lookup_severity_uses_alias_when_primary_id_has_no_rating():
    documents = {
        "GHSA-test": {"database_specific": {"severity": "CRITICAL"}},
    }

    def fetch(vuln_id):
        return documents.get(vuln_id)

    severity = dependency_audit.lookup_severity(
        {"id": "CVE-test", "aliases": ["GHSA-test"]},
        fetch=fetch,
    )

    assert severity == "CRITICAL"


def test_unknown_severity_fails_closed(capsys):
    audit = {
        "dependencies": [
            {
                "name": "example",
                "version": "1.0",
                "vulns": [{"id": "CVE-test", "fix_versions": ["1.1"]}],
            }
        ]
    }

    findings = dependency_audit.collect_findings(audit, severity_lookup=lambda _vuln: "UNKNOWN")

    assert findings == [Finding("example", "1.0", "CVE-test", "UNKNOWN", ("1.1",))]
    assert dependency_audit.report(findings) == 1
    assert "unknown severity" in capsys.readouterr().out


def test_medium_advisories_do_not_fail_the_build(capsys):
    findings = [Finding("example", "1.0", "CVE-test", "MEDIUM", ("1.1",))]

    assert dependency_audit.report(findings) == 0
    assert "PASS" in capsys.readouterr().out


def test_high_advisories_fail_the_build(capsys):
    findings = [Finding("example", "1.0", "CVE-test", "HIGH", ("1.1",))]

    assert dependency_audit.report(findings) == 1
    assert "FAIL" in capsys.readouterr().out
