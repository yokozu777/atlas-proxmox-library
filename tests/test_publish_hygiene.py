"""Publish surface for atlas-proxmox-library."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOTS = (
    REPO_ROOT / "proxmoxlib",
    REPO_ROOT / "roles",
    REPO_ROOT / "README.md",
)


class PublishHygieneTest(unittest.TestCase):
    def test_license_security_and_ci(self) -> None:
        self.assertTrue((REPO_ROOT / "LICENSE").is_file())
        self.assertIn("Apache License", (REPO_ROOT / "LICENSE").read_text(encoding="utf-8"))
        security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("PROXMOX_PASSWORD", security)
        self.assertIn("docs/pre-publish.md", security)
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__/", gitignore)
        self.assertTrue((REPO_ROOT / ".github" / "workflows" / "ci.yml").is_file())
        self.assertTrue((REPO_ROOT / "docs" / "pre-publish.md").is_file())
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("LICENSE", readme)
        self.assertIn("tests/run_ci.sh", readme)

    def test_product_sources_have_no_org_fingerprint(self) -> None:
        for root in PRODUCT_ROOTS:
            paths = [root] if root.is_file() else root.rglob("*")
            for path in paths:
                if not path.is_file() or "__pycache__" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("mxhash", text.lower(), str(path))
                self.assertNotIn("BEGIN OPENSSH PRIVATE", text, str(path))
                self.assertNotIn("BEGIN RSA PRIVATE", text, str(path))
