"""Production dependency audit for Agora.

Runs the same audits the PR1C exit criteria require and reports any open
High/Critical findings with a non-zero exit code.

Usage:
    .venv/bin/python -m scripts.dependency_audit
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[1] / "apps" / "web"
NPM_REGISTRY = "https://registry.npmjs.org"

HIGH_CRITICAL = {"high", "critical"}


def audit_python() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "--format", "json"],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ["pip-audit produced no JSON output; check it is installed"]
    findings = []
    for dependency in data.get("dependencies", []):
        for vulnerability in dependency.get("vulns", []):
            findings.append(
                f"{dependency['name']} {dependency.get('version', '?')} "
                f"{vulnerability.get('id')} fix={vulnerability.get('fix_versions')}"
            )
    return findings


def audit_node() -> list[str]:
    result = subprocess.run(
        ["npm", "audit", "--omit=dev", "--json", "--registry", NPM_REGISTRY],
        cwd=WEB_DIR,
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ["npm audit produced no JSON output; check npm is configured"]
    findings = []
    for name, vulnerability in data.get("vulnerabilities", {}).items():
        if vulnerability.get("severity") in HIGH_CRITICAL:
            findings.append(f"{name}: {vulnerability['severity']}")
    return findings


def main() -> int:
    python_findings = audit_python()
    node_findings = audit_node()
    print(f"pip-audit findings: {len(python_findings)}")
    for finding in python_findings:
        print(f"  {finding}")
    print(f"npm audit (--omit=dev) High/Critical findings: {len(node_findings)}")
    for finding in node_findings:
        print(f"  {finding}")
    if python_findings or node_findings:
        return 1
    print("No open High/Critical production dependency findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
