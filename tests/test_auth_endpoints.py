"""Unit and Integration tests for ECMT AI Authentication & Team Allowlist."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app, JWT_SECRET, APPROVED_TEAM_EMAILS
import jwt
from datetime import datetime


client = TestClient(app)


def test_auth_me_unauthorized_without_token():
    """Verify /api/auth/me rejects requests without authorization token."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Missing Authorization" in res.json()["detail"]


def test_auth_me_with_valid_session_token():
    """Verify /api/auth/me extracts verified user claims from valid JWT session token."""
    now_ts = int(datetime.utcnow().timestamp())
    payload = {
        "sub": "google_1092837465",
        "email": "scientist@ecmt.ai",
        "name": "Dr. Sarah Chen",
        "picture": "https://example.com/avatar.jpg",
        "provider": "google",
        "iat": now_ts,
        "exp": now_ts + 3600,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is True
    assert data["user"]["sub"] == "google_1092837465"
    assert data["user"]["email"] == "scientist@ecmt.ai"
    assert data["user"]["fullName"] == "Dr. Sarah Chen"


def test_auth_me_rejects_expired_token():
    """Verify /api/auth/me rejects expired session tokens."""
    past_ts = int(datetime.utcnow().timestamp()) - 3600
    payload = {
        "sub": "user_expired_123",
        "email": "expired@ecmt.ai",
        "name": "Expired User",
        "iat": past_ts - 7200,
        "exp": past_ts,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "Session expired" in res.json()["detail"]


def test_credentials_login_generates_signed_session():
    """Verify credentials login generates valid JWT with verified subject identifier."""
    res = client.post(
        "/api/auth/login",
        json={
            "account": "researcher@ecmt.ai",
            "password": "valid_secure_password_123",
            "full_name": "Senior Electrochemist",
            "mode": "login",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "session_token" in data
    assert data["user"]["fullName"] == "Senior Electrochemist"
    assert data["user"]["email"] == "researcher@ecmt.ai"
    assert data["user"]["sub"].startswith("usr_")

    # Verify token can be decoded with server secret
    decoded = jwt.decode(data["session_token"], JWT_SECRET, algorithms=["HS256"])
    assert decoded["email"] == "researcher@ecmt.ai"
    assert decoded["sub"] == data["user"]["sub"]


def test_google_verify_rejects_missing_credential():
    """Verify /api/auth/google/verify rejects empty payload."""
    res = client.post("/api/auth/google/verify", json={"credential": ""})
    assert res.status_code == 400
    assert "Missing Google credential" in res.json()["detail"]


def test_google_verify_with_mocked_verified_token():
    """Verify /api/auth/google/verify succeeds and issues session token for verified Google token."""
    mock_id_info = {
        "sub": "google_sub_987654321",
        "email": "verified.researcher@gmail.com",
        "email_verified": True,
        "name": "Verified Researcher",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
    }
    with patch("backend.main.google_id_token.verify_oauth2_token", return_value=mock_id_info):
        res = client.post("/api/auth/google/verify", json={"credential": "valid_mock_token"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "session_token" in data
        assert data["user"]["sub"] == "google_sub_987654321"
        assert data["user"]["email"] == "verified.researcher@gmail.com"
        assert data["user"]["fullName"] == "Verified Researcher"

        # Verify decoded JWT
        decoded = jwt.decode(data["session_token"], JWT_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == "google_sub_987654321"
        assert decoded["email"] == "verified.researcher@gmail.com"
