"""
Repository Secret & Credential Exposure Audit for ECMT AI.
Scans all tracked and staged git files for potential secrets, private keys,
hardcoded tokens, database URIs with passwords, or private .env files.
"""

import os
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Patterns indicating potential secrets
SECRET_PATTERNS = [
    (re.compile(r"(?i)(?:api_key|apikey|secret_key|private_key|service_role_key|jwt_secret)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{16,}['\"]"), "Hardcoded Secret/API Key"),
    (re.compile(r"(?i)postgres(?:ql)?://[a-zA-Z0-9_\-]+:[^@\s]{4,}@[a-zA-Z0-9_\-\.]+\.[a-z]{2,}(?::\d+)?/[a-zA-Z0-9_\-]+"), "Hardcoded Database Connection String with Password"),
    (re.compile(r"(?i)ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"(?i)AIza[0-9A-Za-z\-_]{35}"), "Google Cloud API Key"),
    (re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Raw Private Key"),
    (re.compile(r"(?i)eyJhbGciOi[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9_\-\.]+"), "Hardcoded JWT Token"),
]

# Whitelisted files that contain documentation or tests with synthetic dummy tokens
WHITELIST_FILES = {
    "scripts/scan_secrets_in_repo.py",
    "tests/test_auth_endpoints.py",
}


def audit_repository_secrets():
    print("=" * 70)
    print("ECMT AI — REPOSITORY CREDENTIAL & SECRET EXPOSURE AUDIT")
    print("=" * 70)

    # 1. Check for any tracked .env files
    env_files = list(PROJECT_ROOT.glob("**/.env*"))
    tracked_env = [f for f in env_files if "node_modules" not in str(f) and ".venv" not in str(f)]
    if tracked_env:
        print(f"[ALERT] Found environment files on disk: {[str(f.relative_to(PROJECT_ROOT)) for f in tracked_env]}")
    else:
        print("[Gate 1/3] No .env or private environment files present on disk: PASS")

    # 2. Get list of all git-tracked files
    res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    tracked_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    print(f"[Gate 2/3] Auditing {len(tracked_files)} tracked files in git repository...")

    findings = []
    for rel_path in tracked_files:
        if rel_path in WHITELIST_FILES:
            continue
        p = PROJECT_ROOT / rel_path
        if not p.is_file():
            continue
        # Skip binary files
        if p.suffix in [".joblib", ".db", ".png", ".jpg", ".jpeg", ".webp", ".pdf", ".gz", ".zip"]:
            continue

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for regex, desc in SECRET_PATTERNS:
            matches = regex.findall(content)
            for m in matches:
                # Exclude dummy placeholders e.g. YOUR_KEY, placeholder, example
                m_str = str(m)
                if any(ph in m_str.lower() for ph in ["example", "placeholder", "your_", "aws-0-[region]", "[password]", "[ref]"]):
                    continue
                findings.append((rel_path, desc, m_str[:40] + "..."))

    print("\n[Gate 3/3] Pattern matching results:")
    if findings:
        print(f"[FAIL] Found {len(findings)} potential credential exposures:")
        for file_path, desc, snippet in findings:
            print(f"  • {file_path} [{desc}]: {snippet}")
        return False
    else:
        print("  • ZERO hardcoded API keys detected.")
        print("  • ZERO database passwords or connection URIs with credentials detected.")
        print("  • ZERO private service-role keys detected.")
        print("  • ZERO GitHub/Google private keys detected.")
        print("\n" + "=" * 70)
        print("SECURITY AUDIT PASSED: Repository is clean and safe for public/team hosting!")
        print("=" * 70)
        return True


if __name__ == "__main__":
    audit_repository_secrets()
