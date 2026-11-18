
"""Persistent storage for reviewed PDF literature extractions."""

import json
import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "literature_review.db"
)


def init_review_db():
    """Create the review database and table if they do not exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_pdf TEXT NOT NULL,
                page_number INTEGER,
                reference TEXT,
                composition TEXT,
                extracted_data TEXT NOT NULL,
                evidence_quote TEXT,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT
            )
            """
        )
        


def save_extraction(
    source_pdf: str,
    record: dict,
    status: str = "pending",
) -> int:
    """Save one extracted record and return its database ID."""
    if status not in {"pending", "approved", "rejected"}:
        raise ValueError("Invalid review status.")

    init_review_db()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO extraction_reviews (
                source_pdf, page_number, reference, composition,
                extracted_data, evidence_quote, status, reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 
                    CASE WHEN ? = 'pending'
                         THEN NULL ELSE CURRENT_TIMESTAMP END)
            """,
            (
                source_pdf,
                record.get("page"),
                record.get("reference"),
                record.get("composition"),
                json.dumps(record, ensure_ascii=False),
                record.get("evidence_quote"),
                status,
                status,
            ),
        )
        return cursor.lastrowid


def update_review(review_id: int, record: dict, status: str):
    """Update an extracted record and its review decision, safely preserving fields."""
    if status not in {"pending", "approved", "rejected"}:
        raise ValueError("Invalid review status.")

    init_review_db()

    existing = get_review(review_id)
    if not existing:
        raise ValueError(f"Review ID {review_id} does not exist.")

    page_val = record.get("page") if record.get("page") is not None else existing.get("page_number")
    ref_val = record.get("reference") if record.get("reference") is not None else existing.get("reference")
    comp_val = record.get("composition") if record.get("composition") is not None else existing.get("composition")
    quote_val = record.get("evidence_quote") if record.get("evidence_quote") is not None else existing.get("evidence_quote")

    merged_data = existing.get("extracted_data") or {}
    if isinstance(merged_data, str):
        try:
            merged_data = json.loads(merged_data)
        except Exception:
            merged_data = {}
    merged_data.update(record)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            UPDATE extraction_reviews
            SET page_number = ?,
                reference = ?,
                composition = ?,
                extracted_data = ?,
                evidence_quote = ?,
                status = ?,
                reviewed_at = CASE
                    WHEN ? = 'pending' THEN NULL
                    ELSE CURRENT_TIMESTAMP
                END
            WHERE id = ?
            """,
            (
                page_val,
                ref_val,
                comp_val,
                json.dumps(merged_data, ensure_ascii=False),
                quote_val,
                status,
                status,
                review_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Review ID {review_id} does not exist.")


def list_reviews(status: str | None = None) -> list[dict]:
    """Return saved review records, optionally filtered by status."""
    init_review_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        if status is None:
            rows = conn.execute(
                "SELECT * FROM extraction_reviews ORDER BY id DESC"
            ).fetchall()
        else:
            if status not in {"pending", "approved", "rejected"}:
                raise ValueError("Invalid review status.")

            rows = conn.execute(
                """
                SELECT * FROM extraction_reviews
                WHERE status = ?
                ORDER BY id DESC
                """,
                (status,),
            ).fetchall()

    results = []

    for row in rows:
        item = dict(row)
        item["extracted_data"] = json.loads(item["extracted_data"])
        results.append(item)

    return results


def get_review(review_id: int) -> dict | None:
    """Return a single review record by ID or None if not found."""
    init_review_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM extraction_reviews WHERE id = ?",
            (review_id,),
        ).fetchone()

        if row is None:
            return None

        item = dict(row)
        item["extracted_data"] = json.loads(item["extracted_data"])
        return item


def find_matching_review(
    source_pdf: str,
    page_number: int | None = None,
    composition: str | None = None,
    reference: str | None = None,
) -> int | None:
    """Find the most recent review ID matching the source PDF and record identity."""
    init_review_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT id FROM extraction_reviews WHERE source_pdf = ?"
        params: list[object] = [source_pdf]

        if page_number is not None:
            query += " AND page_number = ?"
            params.append(page_number)
        if composition is not None:
            query += " AND composition = ?"
            params.append(composition)
        if reference is not None:
            query += " AND reference = ?"
            params.append(reference)

        query += " ORDER BY id DESC LIMIT 1"
        row = conn.execute(query, params).fetchone()
        return row["id"] if row else None
