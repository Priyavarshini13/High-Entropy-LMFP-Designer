
import sqlite3

import pandas as pd

from literature import dataset_export
from literature.review_store import DB_PATH


def test_preview_does_not_modify_master_csv(tmp_path, monkeypatch):
    """A dry-run preview must never modify the master CSV."""
    csv_path = tmp_path / "literature_reference.csv"

    master = pd.DataFrame(
        [
            {
                column: None
                for column in dataset_export.EXPECTED_COLUMNS
            }
        ]
    )
    master["Sample_ID"] = "P1_Sample_1"
    master["Paper_ID"] = "P1"
    master["Record_Classification"] = "LITERATURE_REPORTED"
    master.to_csv(csv_path, index=False, encoding="utf-8-sig")

    monkeypatch.setattr(dataset_export, "CSV_PATH", csv_path)
    monkeypatch.setattr(dataset_export, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(dataset_export, "list_reviews", lambda status=None: [])

    before = csv_path.read_bytes()
    result = dataset_export.export_approved_reviews(dry_run=True)

    assert result["status"] == "nothing_to_export"
    assert result["master_records"] == 1
    assert csv_path.read_bytes() == before


def test_preview_reports_empty_review_database(tmp_path, monkeypatch):
    """No approved reviews should result in an empty preview."""
    csv_path = tmp_path / "literature_reference.csv"

    pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS).to_csv(
        csv_path, index=False, encoding="utf-8-sig"
    )

    monkeypatch.setattr(dataset_export, "CSV_PATH", csv_path)
    monkeypatch.setattr(dataset_export, "list_reviews", lambda status=None: [])

    result = dataset_export.preview_approved_exports()

    assert result["master_records"] == 0
    assert result["approved_reviews"] == 0
    assert result["exportable_records"] == 0
    assert result["blocked_records"] == 0


def test_candidate_without_sample_and_paper_identity_is_blocked():
    """The exporter must not invent a sample ID or paper ID."""
    review = {
        "id": 42,
        "source_pdf": "test-paper.pdf",
        "page_number": 3,
        "extracted_data": {
            "composition": "LiMn0.5Fe0.5PO4",
            "evidence_quote": "Example evidence from the paper.",
        },
    }

    master = pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS)
    row, errors = dataset_export._make_candidate(review, master)

    assert row["Composition_Formula"] == "LiMn0.5Fe0.5PO4"
    assert row["Sample_ID"] is None
    assert row["Paper_ID"] is None
    assert any("Sample_ID" in error for error in errors)
    assert any("Paper_ID" in error for error in errors)


def test_numeric_measurements_are_not_guessed():
    """Rate labels or values with units must not become numeric targets."""
    assert dataset_export._numeric_value("1C") is None
    assert dataset_export._numeric_value("150 mAh/g") is None
    assert dataset_export._numeric_value("150") == 150.0
    assert dataset_export._numeric_value(None) is None


def test_expected_schema_has_41_columns():
    """The exporter must preserve the established master CSV schema."""
    assert len(dataset_export.EXPECTED_COLUMNS) == 41
    assert len(set(dataset_export.EXPECTED_COLUMNS)) == 41


def test_multiple_retention_measurements_under_different_cycling_conditions():
    """Multi-condition retention must not be mapped to a single numeric column or averaged."""
    multi_retention = (
        "89.45% (500 cycles, 0.1 C), 89.11% (500 cycles, 2 C), 88.68% (500 cycles, 10 C)"
    )
    review = {
        "id": 7,
        "source_pdf": "test-paper.pdf",
        "page_number": 18,
        "extracted_data": {
            "composition": "LiMn0.8Fe0.2PO4",
            "capacity_retention": multi_retention,
            "evidence_quote": "Extracted evidence text.",
        },
    }

    master = pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS)
    row, errors = dataset_export._make_candidate(review, master)

    # Must NOT be mapped to a single numeric column or collapsed/averaged
    assert row["Capacity_Retention_percent"] is None
    # Original measurement string must be preserved in available provenance/remarks
    assert multi_retention in row["Remarks"]
    # Must NOT report a misleading conversion error
    assert not any("is not a plain numeric value" in err for err in errors)
    # Must accurately state that it is retained for manual review
    assert any("retained for manual review" in err for err in errors)
    # Scientific identity validation must remain active
    assert any("Paper_ID" in err for err in errors)


def test_single_plain_numeric_retention_value():
    """A plain numeric retention value can be assigned to Capacity_Retention_percent."""
    review = {
        "id": 8,
        "source_pdf": "test-paper.pdf",
        "page_number": 2,
        "extracted_data": {
            "composition": "LiMn0.7Fe0.3PO4",
            "capacity_retention": "89.45",
            "evidence_quote": "Single retention measurement.",
        },
    }

    master = pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS)
    row, errors = dataset_export._make_candidate(review, master)

    assert row["Capacity_Retention_percent"] == 89.45
    assert not any("Capacity" in err for err in errors)


def test_verified_paper_and_sample_identity_allows_valid_candidate():
    """When reviewer explicitly verifies paper and sample identity, errors are cleared."""
    review = {
        "id": 9,
        "source_pdf": "verified_study.pdf",
        "page_number": 5,
        "extracted_data": {
            "composition": "LiMn0.7Fe0.3PO4",
            "evidence_quote": "Explicit experimental synthesis and rate capacity.",
            "verified_paper_id": "P99",
            "verified_sample_id": "P99_Sample_1",
            "verified_doi": "10.1016/j.jpowsour.2026.01.001",
            "verified_paper_title": "Novel High Performance LMFP Cathode",
            "verified_capacity_0_1c": "154.5",
            "verified_capacity_1c": "142.0",
            "verified_capacity_5c": "118.0",
            "benchmark_retention_percent": "92.0",
            "benchmark_cycle_count": "500",
            "benchmark_c_rate": "1C",
            "retention_condition_verified": True,
        },
    }

    master = pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS)
    row, errors = dataset_export._make_candidate(review, master)

    assert errors == []
    assert row["Paper_ID"] == "P99"
    assert row["Sample_ID"] == "P99_Sample_1"
    assert row["DOI"] == "10.1016/j.jpowsour.2026.01.001"
    assert row["Discharge_Capacity_0_1C_mAh_g"] == 154.5
    assert row["Discharge_Capacity_1C_mAh_g"] == 142.0
    assert row["Discharge_Capacity_5C_mAh_g"] == 118.0
    assert row["Capacity_Retention_percent"] == 92.0
    assert row["Cycle_Life_cycles"] == 500
    assert "Benchmark condition: 92.0% (500 cycles, 1C)" in row["Remarks"]


def test_duplicate_sample_id_is_blocked():
    """Duplicate Sample_ID already present in master dataset must block export."""
    review = {
        "id": 10,
        "source_pdf": "duplicate_study.pdf",
        "page_number": 1,
        "extracted_data": {
            "composition": "LiMn0.8Fe0.2PO4",
            "evidence_quote": "Duplicate measurement.",
            "verified_paper_id": "P1",
            "verified_sample_id": "P1_N-LMFP",  # Already in master
        },
    }

    master = pd.DataFrame([{"Sample_ID": "P1_N-LMFP", "Paper_ID": "P1"}])
    row, errors = dataset_export._make_candidate(review, master)

    assert any("already exists in master dataset" in err for err in errors)
    assert any("Duplicate samples are prohibited" in err for err in errors)


def test_reviewer_selected_retention_disambiguation_preserves_all_conditions():
    """Reviewer disambiguation of multi-condition retention preserves full extracted string."""
    multi_retention = "89.45% (500 cycles, 0.1 C), 89.11% (500 cycles, 2 C), 88.68% (500 cycles, 10 C)"
    review = {
        "id": 11,
        "source_pdf": "multi_retention.pdf",
        "page_number": 8,
        "extracted_data": {
            "composition": "LiMn0.8Fe0.2PO4",
            "capacity_retention": multi_retention,
            "evidence_quote": "Extended cycling life across multiple C-rates.",
            "verified_paper_id": "P50",
            "verified_sample_id": "P50_Sample_1",
            "benchmark_retention_percent": "89.45",
            "benchmark_cycle_count": "500",
            "benchmark_c_rate": "0.1C",
            "retention_condition_verified": True,
        },
    }

    master = pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS)
    row, errors = dataset_export._make_candidate(review, master)

    assert errors == []
    assert row["Capacity_Retention_percent"] == 89.45
    assert row["Cycle_Life_cycles"] == 500
    assert "Benchmark condition: 89.45% (500 cycles, 0.1C)" in row["Remarks"]
    assert f"All extracted conditions: {multi_retention}" in row["Remarks"]


def test_unverified_multi_condition_retention_remains_blocked():
    """If benchmark retention is entered but checkbox is not confirmed, record remains blocked."""
    multi_retention = "89.45% (500 cycles, 0.1 C), 89.11% (500 cycles, 2 C)"
    review = {
        "id": 12,
        "source_pdf": "unverified.pdf",
        "page_number": 4,
        "extracted_data": {
            "composition": "LiMn0.8Fe0.2PO4",
            "capacity_retention": multi_retention,
            "evidence_quote": "Evidence.",
            "verified_paper_id": "P51",
            "verified_sample_id": "P51_Sample_1",
            "benchmark_retention_percent": "89.45",
            "benchmark_cycle_count": "500",
            "retention_condition_verified": False,
        },
    }

    master = pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS)
    row, errors = dataset_export._make_candidate(review, master)

    assert any("must be explicitly verified before export" in err for err in errors)


def test_invalid_rate_capacity_measurement_is_blocked():
    """Invalid numeric or impossible capacity values are rejected."""
    review = {
        "id": 13,
        "source_pdf": "invalid_cap.pdf",
        "page_number": 3,
        "extracted_data": {
            "composition": "LiMn0.8Fe0.2PO4",
            "evidence_quote": "Evidence text.",
            "verified_paper_id": "P52",
            "verified_sample_id": "P52_Sample_1",
            "verified_capacity_0_1c": "not_a_number",
        },
    }

    master = pd.DataFrame(columns=dataset_export.EXPECTED_COLUMNS)
    row, errors = dataset_export._make_candidate(review, master)

    assert any("is not a plain numeric value" in err for err in errors)


def test_real_export_creates_backup_before_writing(tmp_path, monkeypatch):
    """When a verified review is exported, a backup is created before writing to CSV."""
    csv_path = tmp_path / "literature_reference.csv"
    backup_dir = tmp_path / "backups"

    initial_df = pd.DataFrame(
        [
            {
                col: (f"Init_{col}" if col == "Sample_ID" else None)
                for col in dataset_export.EXPECTED_COLUMNS
            }
        ]
    )
    initial_df["Paper_ID"] = "Init_P"
    initial_df["Record_Classification"] = "LITERATURE_REPORTED"
    initial_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    verified_review = {
        "id": 20,
        "source_pdf": "test_export.pdf",
        "page_number": 7,
        "extracted_data": {
            "composition": "LiMn0.7Fe0.3PO4",
            "evidence_quote": "Verified test export evidence.",
            "verified_paper_id": "P200",
            "verified_sample_id": "P200_Sample_1",
            "verified_capacity_0_1c": "155.0",
        },
    }

    monkeypatch.setattr(dataset_export, "CSV_PATH", csv_path)
    monkeypatch.setattr(dataset_export, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(
        dataset_export, "list_reviews", lambda status=None: [verified_review]
    )

    # 1. Dry run should NOT modify CSV and NOT create backup
    dry_result = dataset_export.export_approved_reviews(dry_run=True)
    assert dry_result["status"] == "dry_run"
    assert dry_result["eligible_records"] == 1
    assert not backup_dir.exists()
    assert len(pd.read_csv(csv_path)) == 1

    # 2. Real export creates backup and appends row
    real_result = dataset_export.export_approved_reviews(dry_run=False)
    assert real_result["status"] == "exported"
    assert real_result["added_records"] == 1
    assert real_result["total_records"] == 2
    assert backup_dir.exists()
    backups = list(backup_dir.glob("*.csv"))
    assert len(backups) == 1

    # Verify updated CSV has exact 41 columns
    updated_df = pd.read_csv(csv_path)
    assert len(updated_df) == 2
    assert list(updated_df.columns) == dataset_export.EXPECTED_COLUMNS


def test_contaminated_record_is_blocked_from_export(tmp_path, monkeypatch):
    """Review #6 with is_test_contaminated cannot be exported even if marked approved."""
    csv_path = tmp_path / "literature_reference.csv"
    backup_dir = tmp_path / "backups"

    master = pd.DataFrame(
        [
            {
                column: None
                for column in dataset_export.EXPECTED_COLUMNS
            }
        ]
    )
    master["Sample_ID"] = "P1_Sample_1"
    master["Paper_ID"] = "P1"
    master["Record_Classification"] = "LITERATURE_REPORTED"
    master.to_csv(csv_path, index=False, encoding="utf-8-sig")

    contaminated_review = {
        "id": 6,
        "source_pdf": "test-paper.pdf",
        "page_number": 18,
        "status": "approved",
        "extracted_data": {
            "composition": "LiMn0.8Fe0.2PO4",
            "evidence_quote": "Evidence quote",
            "verified_paper_id": "P_TEST",
            "verified_sample_id": "S_TEST",
            "is_test_contaminated": True,
            "audit_note": "CONTAMINATED BY TEST DATA",
        },
    }

    monkeypatch.setattr(dataset_export, "CSV_PATH", csv_path)
    monkeypatch.setattr(dataset_export, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(
        dataset_export, "list_reviews", lambda status=None: [contaminated_review]
    )

    # 1. Candidate validation must produce test data contamination error
    row, errors = dataset_export._make_candidate(contaminated_review, master)
    assert any("test data contamination" in err.lower() for err in errors)

    # 2. Preview approved exports must report 0 exportable and 1 blocked
    preview = dataset_export.preview_approved_exports()
    assert preview["approved_reviews"] == 1
    assert preview["exportable_records"] == 0
    assert preview["blocked_records"] == 1
    assert any(
        "test data contamination" in err.lower()
        for err in preview["records"][0]["errors"]
    )

    # 3. Even on real export execution (dry_run=False), export must be refused
    result = dataset_export.export_approved_reviews(dry_run=False)
    assert result["status"] == "no_eligible_records"
    assert result["csv_modified"] is False
    assert result["blocked_records"] == 1
    assert not backup_dir.exists()

    # Master CSV must remain completely untouched
    df_after = pd.read_csv(csv_path)
    assert len(df_after) == 1


