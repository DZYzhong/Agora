import json
import re
from pathlib import Path

from scripts.dependency_audit import audit_node, audit_python


def test_dependency_audit_script_exists_and_runs_clean():
    script = Path("scripts/dependency_audit.py")
    assert script.exists()
    assert "pip_audit" in script.read_text()
    assert "npm" in script.read_text()

    # Both audits currently report zero findings (verified against the official
    # npm registry and the installed Python environment).
    assert audit_python() == []
    assert audit_node() == []


def test_next_is_pinned_to_patched_release_and_transitive_highs_are_overridden():
    package = json.loads(Path("apps/web/package.json").read_text())
    assert "next" in package["dependencies"]
    overrides = package.get("overrides", {})
    assert overrides.get("postcss", "").startswith("^8.4.32")
    assert overrides.get("sharp", "").startswith("^0.35")

    lock = Path("apps/web/package-lock.json").read_text()
    next_match = re.search(r'"node_modules/next": \{[^}]*"version": "([^"]+)"', lock)
    assert next_match is not None
    assert next_match.group(1) >= "15.5.24"


def test_container_images_are_pinned_not_latest():
    compose = Path("infra/docker-compose.yml").read_text()
    images = re.findall(r"image:\s*([^\s]+)", compose)
    assert images, "no images found"
    assert all(not image.endswith(":latest") for image in images), f"unpinned latest: {images}"
