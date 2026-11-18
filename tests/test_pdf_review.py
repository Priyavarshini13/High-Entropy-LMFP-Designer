
import json
import sqlite3

import pytest

from literature import review_store


@pytest.fixture
def temporary_review_db(tmp_path, monkeypatch):
    """Use a temporary database so tests never alter project data."""
    test_db = tmp_path / "literature_review.db"
    monkeypatch.setattr(review_store, "DB_PATH", test_db)
    return test_db


def test_save_and_list_pending_record(temporary_review_db):
    record = {
        "page": 4,
        "composition": "LiMn0.5Fe0.5PO4",
        "reference": "[12]",
        "evidence_quote": "Reported discharge capacity",
    }

    review_id = review_store.save_extraction(
        source_pdf="sample.pdf",
        record=record,
        status="pending",
    )

    results = review_store.list_reviews(status="pending")

    assert len(results) == 1
    assert results[0]["id"] == review_id
    assert results[0]["source_pdf"] == "sample.pdf"
    assert results[0]["page_number"] == 4
    assert results[0]["extracted_data"] == record


def test_update_review_status(temporary_review_db):
    record = {
        "page": 2,
        "composition": "LiMn0.6Fe0.4PO4",
        "evidence_quote": "Experimental result",
    }

    review_id = review_store.save_extraction(
        source_pdf="paper.pdf",
        record=record,
        status="pending",
    )

    updated_record = {
        **record,
        "evidence_quote": "Verified experimental result",
    }

    review_store.update_review(
        review_id=review_id,
        record=updated_record,
        status="approved",
    )

    approved = review_store.list_reviews(status="approved")

    assert len(approved) == 1
    assert approved[0]["id"] == review_id
    assert approved[0]["extracted_data"] == updated_record
    assert approved[0]["reviewed_at"] is not None
    assert review_store.list_reviews(status="pending") == []


def test_invalid_review_status_is_rejected(temporary_review_db):
    with pytest.raises(ValueError, match="Invalid review status"):
        review_store.save_extraction(
            source_pdf="paper.pdf",
            record={"page": 1},
            status="verified",
        )

def test_update_nonexistent_review_raises_error(temporary_review_db):
    with pytest.raises(ValueError, match="does not exist"):
        review_store.update_review(
            review_id=99999,
            record={"page": 1, "composition": "LiMn0.5Fe0.5PO4"},
            status="approved",
        )


def test_save_once_then_update_same_review_id(temporary_review_db):
    from literature.pdf_review import _save_or_update_review

    state = {}
    record = {
        "page": 5,
        "composition": "LiMn0.7Fe0.3PO4",
        "reference": "[15]",
        "evidence_quote": "Initial extraction",
    }
    review_key = "test_paper.pdf_record_0_page_5"

    # First save creates the review record
    review_id_1, created_1 = _save_or_update_review(
        record=record,
        status="pending",
        review_key=review_key,
        source_pdf="test_paper.pdf",
        state_store=state,
    )
    assert created_1 is True
    assert isinstance(review_id_1, int)

    # Subsequent update with edited data reuses the same review ID
    edited_record = {
        **record,
        "evidence_quote": "User edited evidence",
    }
    review_id_2, created_2 = _save_or_update_review(
        record=edited_record,
        status="approved",
        review_key=review_key,
        source_pdf="test_paper.pdf",
        state_store=state,
    )
    assert created_2 is False
    assert review_id_2 == review_id_1

    # Database contains exactly one row
    all_reviews = review_store.list_reviews()
    assert len(all_reviews) == 1
    assert all_reviews[0]["id"] == review_id_1
    assert all_reviews[0]["status"] == "approved"
    assert all_reviews[0]["extracted_data"]["evidence_quote"] == "User edited evidence"

    # A genuinely new extraction or different PDF creates a separate review ID
    review_id_3, created_3 = _save_or_update_review(
        record={"page": 10, "composition": "LiMn0.8Fe0.2PO4"},
        status="pending",
        review_key="other_paper.pdf_record_0_page_10",
        source_pdf="other_paper.pdf",
        state_store=state,
    )
    assert created_3 is True
    assert review_id_3 != review_id_1
    assert len(review_store.list_reviews()) == 2


def test_approve_and_reject_status_transitions(temporary_review_db):
    record = {
        "page": 1,
        "composition": "LiMn0.8Fe0.2PO4",
        "evidence_quote": "Experimental evidence",
    }

    # 1. Start as pending
    review_id = review_store.save_extraction(
        source_pdf="transition_test.pdf",
        record=record,
        status="pending",
    )
    r1 = review_store.get_review(review_id)
    assert r1["status"] == "pending"
    assert r1["reviewed_at"] is None

    # 2. Transition to approved
    review_store.update_review(review_id, record, status="approved")
    r2 = review_store.get_review(review_id)
    assert r2["status"] == "approved"
    assert r2["reviewed_at"] is not None

    # 3. Transition to rejected
    review_store.update_review(review_id, record, status="rejected")
    r3 = review_store.get_review(review_id)
    assert r3["status"] == "rejected"
    assert r3["reviewed_at"] is not None

    # 4. Transition back to approved
    review_store.update_review(review_id, record, status="approved")
    r4 = review_store.get_review(review_id)
    assert r4["status"] == "approved"

    # Total row count never increased beyond 1
    assert len(review_store.list_reviews()) == 1


def test_repeated_extraction_same_paper_safely_handles_existing_record(temporary_review_db):
    from literature.pdf_review import _save_or_update_review

    record = {
        "page": 18,
        "composition": "LiMn0.8Fe0.2PO4",
        "reference": "[29]",
        "evidence_quote": "Initial extraction",
    }
    source_pdf = "repeated_paper.pdf"

    # Initial session extraction and approval
    session_1 = {}
    rev_id_1, created_1 = _save_or_update_review(
        record=record,
        status="approved",
        review_key=f"{source_pdf}_record_0_page_18",
        source_pdf=source_pdf,
        state_store=session_1,
    )
    assert created_1 is True

    # New session: session state is empty, user re-extracts the same paper
    session_2 = {}
    updated_record = {
        **record,
        "evidence_quote": "Re-extracted with corrected text",
    }
    rev_id_2, created_2 = _save_or_update_review(
        record=updated_record,
        status="approved",
        review_key=f"{source_pdf}_record_0_page_18",
        source_pdf=source_pdf,
        state_store=session_2,
    )

    # Must safely reuse the existing review ID and not create duplicate rows
    assert created_2 is False
    assert rev_id_2 == rev_id_1
    assert len(review_store.list_reviews()) == 1
    assert review_store.get_review(rev_id_1)["extracted_data"]["evidence_quote"] == "Re-extracted with corrected text"