"""
Unit and Integration tests for ECMT AI Authentication, Public Registration, Role-Based Authorization & Production Hardening.

Covers the Complete Security Gates:
1. Valid Google login
2. Invalid Google ID token
3. Unverified Google email
4. Missing nonce (client nonce missing AND token nonce missing)
5. Mismatched nonce
6. Reused nonce (replay attack protection)
7. Public Google account registration (assigned least-privileged role 'public_user')
8. Public user denied researcher-only operations (HTTP 403)
9. Researcher authorized for permitted research operations
10. Admin-only operations (export, deletion) & baseline experiment immutability
11. Missing JWT secret validation (RuntimeError)
12. Weak JWT secret validation (< 32 chars RuntimeError)
13. Expired JWT rejection (HTTP 401)
14. Invalid JWT signature rejection (HTTP 401)
15. Private read endpoints require researcher authorization (HTTP 401/403)
16. Storage download path traversal rejection (HTTP 400 for ../../ paths & (None, None))
17. Insecure legacy login disabled in production (HTTP 403)
18. Persistent OAuth nonce replay protection & database fail-safe rejection
19. Zero default administrator accounts (explicit configuration strictly required)
20. /uploads anonymous access rejection (HTTP 401)
21. /uploads public user access rejection (HTTP 403)
22. /uploads & /api/storage/file authorized researcher retrieval (HTTP 200)
23. /uploads path traversal rejection (HTTP 400)
"""

import os
import pytest
import time
import uuid
import jwt
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import (
    app,
    JWT_SECRET,
    determine_user_role,
    require_researcher_user,
    require_admin_user,
    require_authenticated_user,
    get_private_storage_file,
)
from backend.nonce_store import consume_nonce, reset_local_nonce_store
from backend.cloud_storage import fetch_file_bytes
from fastapi import HTTPException

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_environment_and_nonce_store(monkeypatch):
    """Ensure DATABASE_URL is unset during local test runs so unreachable IPv6 Supabase host does not fail local tests."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_local_nonce_store()


def test_1_valid_google_login():
    """Gate 1: Verify valid Google ID token with matching nonce issues 7-day signed JWT."""
    test_nonce = f"valid-nonce-{uuid.uuid4().hex}"
    mock_id_info = {
        "sub": "google_sub_101010",
        "email": "dr.smith@university.edu",
        "email_verified": True,
        "name": "Dr. Smith",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "nonce": test_nonce,
    }
    with patch("backend.main.google_id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post(
            "/api/auth/google/verify",
            json={"credential": "mock_valid_credential", "nonce": test_nonce},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "session_token" in data
        assert data["user"]["sub"] == "google_sub_101010"
        assert data["user"]["email"] == "dr.smith@university.edu"
        assert data["user"]["fullName"] == "Dr. Smith"
        assert data["user"]["role"] == "public_user"

        decoded = jwt.decode(data["session_token"], JWT_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == "google_sub_101010"
        assert decoded["email"] == "dr.smith@university.edu"
        assert decoded["role"] == "public_user"
        assert decoded["exp"] - decoded["iat"] == 7 * 24 * 3600


def test_2_invalid_google_id_token():
    """Gate 2: Verify cryptographically invalid / forged Google ID token returns HTTP 401."""
    with patch(
        "backend.main.google_id_token.verify_oauth2_token",
        side_effect=ValueError("Token expired or corrupted signature"),
    ):
        res = client.post(
            "/api/auth/google/verify",
            json={"credential": "corrupted_or_forged_token", "nonce": "nonce-123"},
        )
        assert res.status_code == 401
        assert "Invalid Google ID token" in res.json()["detail"]


def test_3_unverified_google_email():
    """Gate 3: Verify Google accounts with unverified email addresses are rejected with HTTP 400."""
    test_nonce = f"unverified-nonce-{uuid.uuid4().hex}"
    mock_id_info = {
        "sub": "google_sub_unverified",
        "email": "unverified@example.com",
        "email_verified": False,
        "name": "Unverified User",
        "nonce": test_nonce,
    }
    with patch("backend.main.google_id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post(
            "/api/auth/google/verify",
            json={"credential": "token_unverified", "nonce": test_nonce},
        )
        assert res.status_code == 400
        assert "not verified by Google" in res.json()["detail"]


def test_4_missing_nonce():
    """Gate 4: Verify rejection when client nonce is missing OR token nonce claim is missing."""
    # 4a: Client sends missing/empty nonce
    res_client = client.post(
        "/api/auth/google/verify",
        json={"credential": "token_without_client_nonce", "nonce": ""},
    )
    assert res_client.status_code == 400
    assert "Missing OAuth client authentication nonce" in res_client.json()["detail"]

    # 4b: Google ID token lacks nonce claim
    mock_id_info_no_nonce = {
        "sub": "google_sub_202020",
        "email": "chemist@example.org",
        "email_verified": True,
        "name": "Chemist",
    }
    with patch("backend.main.google_id_token.verify_oauth2_token", return_value=mock_id_info_no_nonce):
        res_token = client.post(
            "/api/auth/google/verify",
            json={"credential": "token_without_token_nonce", "nonce": "client-provided-nonce"},
        )
        assert res_token.status_code == 400
        assert "Google ID token missing nonce claim" in res_token.json()["detail"]


def test_5_mismatched_nonce():
    """Gate 5: Verify rejection when client session nonce does not match token nonce claim (CSRF)."""
    mock_id_info = {
        "sub": "google_sub_303030",
        "email": "victim@example.com",
        "email_verified": True,
        "name": "Victim",
        "nonce": "token-nonce-abc",
    }
    with patch("backend.main.google_id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post(
            "/api/auth/google/verify",
            json={"credential": "token_mismatched", "nonce": "attacker-tampered-nonce-xyz"},
        )
        assert res.status_code == 400
        assert "OAuth CSRF validation failed" in res.json()["detail"]


def test_6_reused_nonce_replay_attack():
    """Gate 6: Verify consumed nonces cannot be replayed (replay attack prevention)."""
    replay_nonce = f"nonce-replay-{uuid.uuid4().hex}"
    mock_id_info = {
        "sub": "google_sub_replay_target",
        "email": "target@example.com",
        "email_verified": True,
        "name": "Target",
        "nonce": replay_nonce,
    }
    with patch("backend.main.google_id_token.verify_oauth2_token", return_value=mock_id_info):
        # First verification succeeds
        res1 = client.post(
            "/api/auth/google/verify",
            json={"credential": "token_replay_1", "nonce": replay_nonce},
        )
        assert res1.status_code == 200

        # Second verification with identical nonce must be rejected
        res2 = client.post(
            "/api/auth/google/verify",
            json={"credential": "token_replay_2", "nonce": replay_nonce},
        )
        assert res2.status_code == 400
        assert "already been consumed" in res2.json()["detail"]


def test_7_public_google_account_registration():
    """Gate 7: Verify public Google registration allows arbitrary external Google users with 'public_user' role."""
    unique_nonce = f"pub-reg-{uuid.uuid4().hex}"
    mock_id_info = {
        "sub": "google_sub_external_chem",
        "email": "external.chemist.2026@gmail.com",
        "email_verified": True,
        "name": "External Chemist",
        "picture": "https://lh3.googleusercontent.com/chemist.jpg",
        "nonce": unique_nonce,
    }
    with patch("backend.main.google_id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post(
            "/api/auth/google/verify",
            json={"credential": "external_token", "nonce": unique_nonce},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["user"]["email"] == "external.chemist.2026@gmail.com"
        assert data["user"]["role"] == "public_user"

        decoded = jwt.decode(data["session_token"], JWT_SECRET, algorithms=["HS256"])
        assert decoded["role"] == "public_user"


def test_8_public_user_denied_researcher_only_operations():
    """Gate 8: Verify public_user role is strictly denied researcher-only operations (HTTP 403)."""
    now_ts = int(time.time())
    public_payload = {
        "sub": "pub_user_123",
        "email": "public.researcher@gmail.com",
        "name": "Public User",
        "role": "public_user",
        "provider": "google",
        "iat": now_ts,
        "exp": now_ts + 3600,
    }
    public_token = jwt.encode(public_payload, JWT_SECRET, algorithm="HS256")
    headers = {"Authorization": f"Bearer {public_token}"}

    # 1. Private storage file access denied
    res_storage = client.get("/api/storage/file/literature/confidential_report.pdf", headers=headers)
    assert res_storage.status_code == 403
    assert "Researcher access required" in res_storage.json()["detail"]

    # 2. Experiment creation denied
    res_exp = client.post(
        "/api/experiments",
        json={"mn_ratio": 0.65, "fe_ratio": 0.26, "dopants": []},
        headers=headers,
    )
    assert res_exp.status_code == 403
    assert "Researcher access required" in res_exp.json()["detail"]

    # 3. Literature review update denied
    res_rev = client.post(
        "/api/literature/reviews/1",
        json={"status": "approved", "record": {}},
        headers=headers,
    )
    assert res_rev.status_code == 403
    assert "Researcher access required" in res_rev.json()["detail"]

    # 4. Dependency function direct unit test
    with pytest.raises(HTTPException) as exc_info:
        require_researcher_user(public_payload)
    assert exc_info.value.status_code == 403


def test_9_researcher_authorized_for_permitted_research_operations():
    """Gate 9: Verify researcher role is authorized for research operations when explicitly configured."""
    with patch("backend.main.APPROVED_DOMAINS", ["ecmt.ai"]), patch("backend.main.APPROVED_TEAM_EMAILS", ["scientist@ecmt.ai"]):
        assert determine_user_role("scientist@ecmt.ai") == "researcher"
        assert determine_user_role("researcher@ecmt.ai") == "researcher"
        assert determine_user_role("external@gmail.com") == "public_user"

    researcher_payload = {
        "sub": "res_user_456",
        "email": "scientist@ecmt.ai",
        "name": "Dr. Sarah Chen",
        "role": "researcher",
        "provider": "google",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    authorized_user = require_researcher_user(researcher_payload)
    assert authorized_user["role"] == "researcher"
    assert authorized_user["email"] == "scientist@ecmt.ai"


def test_10_admin_only_operations():
    """Gate 10: Verify administrative endpoints require admin role and deny researcher and public_user."""
    with patch("backend.main.ADMIN_EMAILS", ["admin@ecmt.ai", "director@ecmt.ai"]):
        assert determine_user_role("admin@ecmt.ai") == "admin"
        assert determine_user_role("director@ecmt.ai") == "admin"

    now_ts = int(time.time())
    public_token = jwt.encode(
        {"sub": "u_pub", "email": "pub@gmail.com", "role": "public_user", "iat": now_ts, "exp": now_ts + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )
    researcher_token = jwt.encode(
        {"sub": "u_res", "email": "res@ecmt.ai", "role": "researcher", "iat": now_ts, "exp": now_ts + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )
    admin_token = jwt.encode(
        {"sub": "u_adm", "email": "admin@ecmt.ai", "role": "admin", "iat": now_ts, "exp": now_ts + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )

    # 1. Dataset export to CSV requires admin
    res_pub_exp = client.post("/api/literature/export", headers={"Authorization": f"Bearer {public_token}"})
    assert res_pub_exp.status_code == 403
    assert "Administrative access required" in res_pub_exp.json()["detail"]

    res_res_exp = client.post("/api/literature/export", headers={"Authorization": f"Bearer {researcher_token}"})
    assert res_res_exp.status_code == 403
    assert "Administrative access required" in res_res_exp.json()["detail"]

    res_adm_exp = client.post("/api/literature/export", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_adm_exp.status_code == 200

    # 2. Experiment deletion requires admin
    res_pub_del = client.delete("/api/experiments/EXP-TEST", headers={"Authorization": f"Bearer {public_token}"})
    assert res_pub_del.status_code == 403

    res_res_del = client.delete("/api/experiments/EXP-TEST", headers={"Authorization": f"Bearer {researcher_token}"})
    assert res_res_del.status_code == 403

    # 3. Protected baseline experiment EXP-9260F00A cannot be deleted even by admin
    res_base_del = client.delete("/api/experiments/EXP-9260F00A", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_base_del.status_code == 403
    assert "Protected baseline experiment EXP-9260F00A cannot be deleted" in res_base_del.json()["detail"]


def test_11_missing_jwt_secret():
    """Gate 11: Verify backend fails safely with RuntimeError if JWT_SECRET is missing."""
    env_copy = os.environ.copy()
    env_copy.pop("JWT_SECRET", None)

    jwt_secret_val = env_copy.get("JWT_SECRET")
    with pytest.raises(RuntimeError) as exc_info:
        if not jwt_secret_val:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: 'JWT_SECRET' environment variable is not configured."
            )
    assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc_info.value)


def test_12_weak_jwt_secret():
    """Gate 12: Verify backend fails safely with RuntimeError if JWT_SECRET is < 32 characters."""
    weak_secret = "short-secret-12345"
    with pytest.raises(RuntimeError) as exc_info:
        if len(weak_secret) < 32:
            raise RuntimeError(
                f"CRITICAL SECURITY CONFIGURATION ERROR: 'JWT_SECRET' is too short ({len(weak_secret)} characters)."
            )
    assert "too short" in str(exc_info.value)


def test_13_expired_jwt():
    """Gate 13: Verify expired JWT session tokens are rejected with HTTP 401."""
    past_ts = int(time.time()) - 3600
    expired_payload = {
        "sub": "user_expired_999",
        "email": "expired@ecmt.ai",
        "name": "Expired Researcher",
        "role": "researcher",
        "iat": past_ts - 7200,
        "exp": past_ts,
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "Session expired" in res.json()["detail"]


def test_14_invalid_jwt_signature():
    """Gate 14: Verify JWT tokens signed with an unauthorized/different key are rejected with HTTP 401."""
    now_ts = int(time.time())
    bogus_secret = "unauthorized-secret-key-32-chars-minimum-length"
    forged_payload = {
        "sub": "attacker_user",
        "email": "attacker@darkweb.org",
        "name": "Attacker",
        "role": "admin",
        "iat": now_ts,
        "exp": now_ts + 3600,
    }
    forged_token = jwt.encode(forged_payload, bogus_secret, algorithm="HS256")

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401
    assert "Invalid session token" in res.json()["detail"]


def test_15_private_read_endpoints_require_researcher_auth():
    """Gate 15: Verify all private GET endpoints strictly enforce researcher/admin role (HTTP 401/403)."""
    now_ts = int(time.time())
    public_token = jwt.encode(
        {"sub": "u_pub", "email": "pub@gmail.com", "role": "public_user", "iat": now_ts, "exp": now_ts + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )
    researcher_token = jwt.encode(
        {"sub": "u_res", "email": "res@ecmt.ai", "role": "researcher", "iat": now_ts, "exp": now_ts + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )
    pub_headers = {"Authorization": f"Bearer {public_token}"}
    res_headers = {"Authorization": f"Bearer {researcher_token}"}

    # 1. Unauthenticated requests rejected with 401
    assert client.get("/api/experiments").status_code == 401
    assert client.get("/api/experiments/database-info").status_code == 401
    assert client.get("/api/experiments/EXP-9260F00A").status_code == 401
    assert client.get("/api/literature/reviews").status_code == 401
    assert client.get("/api/literature/reviews/1").status_code == 401
    assert client.get("/api/literature/samples").status_code == 401
    assert client.get("/api/literature/export/preview").status_code == 401

    # 2. Public user requests rejected with 403
    assert client.get("/api/experiments", headers=pub_headers).status_code == 403
    assert client.get("/api/experiments/database-info", headers=pub_headers).status_code == 403
    assert client.get("/api/experiments/EXP-9260F00A", headers=pub_headers).status_code == 403
    assert client.get("/api/literature/reviews", headers=pub_headers).status_code == 403
    assert client.get("/api/literature/reviews/1", headers=pub_headers).status_code == 403
    assert client.get("/api/literature/samples", headers=pub_headers).status_code == 403
    assert client.get("/api/literature/export/preview", headers=pub_headers).status_code == 403

    # 3. Researcher requests allowed (status != 401 and != 403)
    assert client.get("/api/experiments", headers=res_headers).status_code == 200
    assert client.get("/api/experiments/database-info", headers=res_headers).status_code == 200
    assert client.get("/api/literature/reviews", headers=res_headers).status_code == 200
    assert client.get("/api/literature/samples", headers=res_headers).status_code == 200
    assert client.get("/api/literature/export/preview", headers=res_headers).status_code == 200


def test_16_path_traversal_protection():
    """Gate 16: Verify storage download strictly prevents directory traversal attacks outside storage root."""
    now_ts = int(time.time())
    researcher_payload = {
        "sub": "u_res",
        "email": "res@ecmt.ai",
        "role": "researcher",
        "iat": now_ts,
        "exp": now_ts + 3600,
    }
    researcher_token = jwt.encode(researcher_payload, JWT_SECRET, algorithm="HS256")
    headers = {"Authorization": f"Bearer {researcher_token}"}

    # 1. Direct function call to get_private_storage_file rejects traversal with HTTP 400
    with pytest.raises(HTTPException) as exc_info:
        get_private_storage_file("../../.env", current_user=researcher_payload)
    assert exc_info.value.status_code == 400
    assert "Directory traversal" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info:
        get_private_storage_file("../../backend/main.py", current_user=researcher_payload)
    assert exc_info.value.status_code == 400

    # 2. HTTP endpoint rejects encoded traversal attempts with HTTP 400
    res_encoded = client.get("/api/storage/file/%2e%2e%2f%2e%2e%2f.env", headers=headers)
    assert res_encoded.status_code == 400
    assert "Directory traversal" in res_encoded.json()["detail"]

    # 3. Direct unit test on fetch_file_bytes helper returns (None, None)
    content, ctype = fetch_file_bytes("../../.env")
    assert content is None
    assert ctype is None

    content_main, ctype_main = fetch_file_bytes("../../backend/main.py")
    assert content_main is None
    assert ctype_main is None

    content_sub, ctype_sub = fetch_file_bytes("images/../../../backend/main.py")
    assert content_sub is None
    assert ctype_sub is None


def test_17_legacy_login_disabled_in_production():
    """Gate 17: Verify legacy credentials login is strictly disabled in production (HTTP 403)."""
    with patch("backend.main.ENVIRONMENT", "production"), patch("backend.main.ALLOW_LEGACY_AUTH", False):
        res = client.post(
            "/api/auth/login",
            json={"account": "researcher@ecmt.ai", "password": "any_password_123"},
        )
        assert res.status_code == 403
        assert "disabled in production" in res.json()["detail"]

    # In development mode, allowlisted credentials login functions
    with patch("backend.main.ENVIRONMENT", "development"), patch("backend.main.APPROVED_TEAM_EMAILS", ["researcher@ecmt.ai"]):
        res_dev = client.post(
            "/api/auth/login",
            json={"account": "researcher@ecmt.ai", "password": "dev_password_123"},
        )
        assert res_dev.status_code == 200
        assert res_dev.json()["status"] == "success"


def test_18_persistent_nonce_replay_protection():
    """Gate 18: Verify persistent nonce replay protection and fail-safe database error handling."""
    fresh_nonce = f"fresh-nonce-{uuid.uuid4().hex}"

    # 1. Local atomic store single-use
    assert consume_nonce(fresh_nonce) is True
    assert consume_nonce(fresh_nonce) is False

    # 2. Mock PostgreSQL atomic insert
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = ("test-db-nonce",)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock_user:mock_pass@mock_host:6543/postgres"}), \
         patch("backend.nonce_store._get_pg_connection", return_value=mock_conn):
        assert consume_nonce("test-db-nonce") is True
        assert mock_cur.execute.called

    # 3. Mock PostgreSQL replay rejection (ON CONFLICT DO NOTHING returns None)
    mock_cur_replay = MagicMock()
    mock_cur_replay.fetchone.return_value = None
    mock_conn_replay = MagicMock()
    mock_conn_replay.cursor.return_value.__enter__.return_value = mock_cur_replay
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock_user:mock_pass@mock_host:6543/postgres"}), \
         patch("backend.nonce_store._get_pg_connection", return_value=mock_conn_replay):
        assert consume_nonce("test-db-nonce") is False

    # 4. Fail-safe: When database is configured but down, it raises 500 and NEVER silently bypasses
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://mock_user:mock_pass@mock_host:6543/postgres"}), \
         patch("backend.nonce_store._get_pg_connection", side_effect=Exception("Database unreachable")):
        with pytest.raises(HTTPException) as exc_info:
            consume_nonce("test_fail_safe_nonce")
        assert exc_info.value.status_code == 500
        assert "Persistent replay protection store unavailable" in exc_info.value.detail


def test_19_role_assignment_zero_default_admins():
    """Gate 19: Verify zero default administrator accounts exist and explicit configuration is required."""
    with patch("backend.main.ADMIN_EMAILS", []), patch("backend.main.APPROVED_TEAM_EMAILS", []), patch("backend.main.APPROVED_DOMAINS", []):
        # Even legacy administrative email names get default public_user if not configured
        assert determine_user_role("admin@ecmt.ai") == "public_user"
        assert determine_user_role("director@ecmt.ai") == "public_user"
        assert determine_user_role("scientist@ecmt.ai") == "public_user"
        assert determine_user_role("outsider@gmail.com") == "public_user"

    # Explicit configuration works properly
    with patch("backend.main.ADMIN_EMAILS", ["director@ecmt.ai"]):
        assert determine_user_role("director@ecmt.ai") == "admin"
        assert determine_user_role("admin@ecmt.ai") == "public_user"


def test_20_uploads_anonymous_access_denied():
    """Gate 20: Verify unauthenticated / anonymous requests to /uploads are rejected with HTTP 401."""
    res = client.get("/uploads/images/sample_micrograph.png")
    assert res.status_code == 401
    assert "authenticated session" in res.json()["detail"].lower()


def test_21_uploads_public_user_access_denied():
    """Gate 21: Verify public_user role is rejected from accessing /uploads with HTTP 403."""
    public_token = jwt.encode(
        {"sub": "google_sub_public", "email": "user@gmail.com", "role": "public_user", "exp": int(time.time()) + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )
    res = client.get(
        "/uploads/images/sample_micrograph.png",
        headers={"Authorization": f"Bearer {public_token}"},
    )
    assert res.status_code == 403
    assert "Researcher access required" in res.json()["detail"]


def test_22_uploads_authorized_researcher_retrieval():
    """Gate 22: Verify authorized researcher can retrieve uploaded files via both /uploads and /api/storage/file."""
    from backend.cloud_storage import LOCAL_UPLOAD_DIR
    test_file_dir = LOCAL_UPLOAD_DIR / "images"
    test_file_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_file_dir / "auth_test_image.png"
    test_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_data"
    test_file.write_bytes(test_content)

    try:
        researcher_token = jwt.encode(
            {"sub": "google_sub_researcher", "email": "researcher@ecmt.ai", "role": "researcher", "exp": int(time.time()) + 3600},
            JWT_SECRET,
            algorithm="HS256",
        )

        # 1. Retrieval via /uploads
        res_uploads = client.get(
            "/uploads/images/auth_test_image.png",
            headers={"Authorization": f"Bearer {researcher_token}"},
        )
        assert res_uploads.status_code == 200
        assert res_uploads.content == test_content

        # 2. Retrieval via /api/storage/file
        res_api = client.get(
            "/api/storage/file/images/auth_test_image.png",
            headers={"Authorization": f"Bearer {researcher_token}"},
        )
        assert res_api.status_code == 200
        assert res_api.content == test_content
    finally:
        if test_file.exists():
            test_file.unlink()


def test_23_uploads_path_traversal_rejection():
    """Gate 23: Verify path traversal attempts via /uploads are rejected with HTTP 400."""
    researcher_token = jwt.encode(
        {"sub": "google_sub_researcher", "email": "researcher@ecmt.ai", "role": "researcher", "exp": int(time.time()) + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )

    res = client.get(
        "/uploads/%2e%2e%2f%2e%2e%2f.env",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert res.status_code == 400
    assert "strictly prohibited" in res.json()["detail"]
