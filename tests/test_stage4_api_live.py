"""
Automated Live API verification suite for Stage 4 endpoints:
- GET /api/literature/samples
- GET /api/literature/samples/{sample_id}
- POST /api/literature/samples/{sample_id}/resolve
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_samples_unfiltered():
    """Verify GET /api/literature/samples returns all resolved material samples."""
    response = client.get("/api/literature/samples")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 16

    # Verify schema of returned sample entity
    sample = data[0]
    required_keys = {
        "sample_id",
        "paper_id",
        "sample_label",
        "provenance_type",
        "resolution_status",
        "resolution_confidence",
        "base_lmfp_formula",
        "mn_ratio",
        "fe_ratio",
        "dopants",
        "modifications",
        "precursor_salts",
        "measurements",
    }
    assert required_keys.issubset(set(sample.keys()))


def test_get_samples_filter_by_paper_id():
    """Verify filtering by paper_id=srep26686 returns exactly the 3 srep26686 samples."""
    response = client.get("/api/literature/samples?paper_id=srep26686")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    labels = {s["sample_label"] for s in data}
    assert labels == {"SD_NO3", "SD_SO4", "LiMn0.75Fe0.25PO4/rGO"}


def test_get_samples_filter_by_dopant():
    """Verify filtering by dopant returns matching samples."""
    response = client.get("/api/literature/samples?dopant=Ni")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for s in data:
        has_ni = any(d.get("element") == "Ni" or d.get("symbol") == "Ni" for d in s.get("dopants", []))
        assert has_ni or "Ni" in s.get("sample_label", "") or "Ni" in s.get("raw_formula", "")


def test_get_samples_filter_by_min_crate():
    """Verify filtering by min_crate=10.0 returns measurements with c_rate >= 10."""
    response = client.get("/api/literature/samples?paper_id=srep26686&min_crate=10.0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    rgo = next(s for s in data if s["sample_label"] == "LiMn0.75Fe0.25PO4/rGO")
    assert len(rgo["measurements"]) == 2
    for m in rgo["measurements"]:
        assert m["c_rate"] >= 10.0


def test_get_single_sample_valid():
    """Verify GET /api/literature/samples/{sample_id} returns full entity graph."""
    response = client.get("/api/literature/samples/srep26686_SD_NO3")
    assert response.status_code == 200
    data = response.json()
    assert data["sample_id"] == "srep26686_SD_NO3"
    assert data["sample_label"] == "SD_NO3"
    assert data["resolution_status"] == "CONFIRMED_EXPLICIT"
    assert data["provenance_type"] == "PRIMARY_EXPERIMENTAL"
    assert "Fe(NO3)3" in data["precursor_salts"]
    assert "Fe2O3" in data["xrd_phase_purity"]
    assert len(data["measurements"]) == 1
    assert data["measurements"][0]["normalized_value"] == 45.0


def test_get_single_sample_missing():
    """Verify GET /api/literature/samples/{sample_id} returns 404 for non-existent sample."""
    response = client.get("/api/literature/samples/non_existent_sample_xyz")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_post_resolve_sample_valid():
    """Verify POST /api/literature/samples/{sample_id}/resolve updates reviewer metadata."""
    update_payload = {
        "sample_label": "SD_NO3",
        "resolution_status": "CONFIRMED_EXPLICIT",
        "resolution_notes": "Audit verification: nitrate precursor confirmed for SD_NO3.",
        "is_unresolved": False,
    }
    response = client.post("/api/literature/samples/srep26686_SD_NO3/resolve", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] is True
    assert data["sample"]["resolution_notes"] == update_payload["resolution_notes"]
    assert data["sample"]["is_unresolved"] is False

    # Verify retrieval reflects update
    fetch_resp = client.get("/api/literature/samples/srep26686_SD_NO3")
    assert fetch_resp.json()["resolution_notes"] == update_payload["resolution_notes"]


def test_post_resolve_sample_missing():
    """Verify POST /api/literature/samples/{sample_id}/resolve returns 404 for missing sample."""
    payload = {"resolution_status": "AMBIGUOUS"}
    response = client.post("/api/literature/samples/non_existent_sample_xyz/resolve", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_post_resolve_sample_invalid_payload():
    """Verify POST /api/literature/samples/{sample_id}/resolve returns 422 for malformed body."""
    # Sending invalid data type for is_unresolved
    response = client.post(
        "/api/literature/samples/srep26686_SD_NO3/resolve",
        json={"is_unresolved": "invalid_boolean_string_that_cannot_coerce"},
    )
    assert response.status_code == 422


def test_post_resolve_mark_ambiguous_and_revert():
    """Verify reviewer can flag ambiguous sample and revert without data loss."""
    ambig_payload = {
        "resolution_status": "AMBIGUOUS",
        "resolution_notes": "Flagged as ambiguous during audit test.",
        "is_unresolved": True,
    }
    r_ambig = client.post("/api/literature/samples/srep26686_SD_NO3/resolve", json=ambig_payload)
    assert r_ambig.status_code == 200
    assert r_ambig.json()["sample"]["resolution_status"] == "AMBIGUOUS"
    assert r_ambig.json()["sample"]["is_unresolved"] is True

    # Revert to confirmed
    revert_payload = {
        "resolution_status": "CONFIRMED_EXPLICIT",
        "resolution_notes": "Explicit sample designation for nitrate precursor in srep26686.",
        "is_unresolved": False,
    }
    r_revert = client.post("/api/literature/samples/srep26686_SD_NO3/resolve", json=revert_payload)
    assert r_revert.status_code == 200
    assert r_revert.json()["sample"]["resolution_status"] == "CONFIRMED_EXPLICIT"
    assert r_revert.json()["sample"]["is_unresolved"] is False
