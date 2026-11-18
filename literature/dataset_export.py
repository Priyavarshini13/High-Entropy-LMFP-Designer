
"""
Safe exporter for approved PDF literature extractions.

- Reads only approved records from the review database.
- Preserves the existing master CSV column names and order.
- Does not invent missing experimental values.
- Uses dry-run mode by default.
- Creates a backup before writing to the master CSV.
- Does not retrain ML models.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from literature.review_store import list_reviews


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "literature_reference.csv"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

CLASSIFICATION = "LITERATURE_REPORTED"

# These must remain in the exact order used by the master CSV.
EXPECTED_COLUMNS = [
    "Sample_ID",
    "Paper_ID",
    "Paper_Title",
    "DOI",
    "Year",
    "Source_PDF",
    "Composition_Formula",
    "Base_LMFP_Composition",
    "Full_Doped_Composition",
    "Mn_Ratio",
    "Fe_Ratio",
    "Dopant_Element",
    "Dopant_Count",
    "Dopant_Molar_Ratio",
    "Dopant_x_per_fu",
    "Carbon_wt_percent",
    "Synthesis_Method",
    "Calcination_Temp_1_C",
    "Calcination_Time_1_h",
    "Discharge_Capacity_0_05C_mAh_g",
    "Discharge_Capacity_0_1C_mAh_g",
    "Discharge_Capacity_1C_mAh_g",
    "Discharge_Capacity_2C_mAh_g",
    "Discharge_Capacity_5C_mAh_g",
    "Initial_Coulombic_Efficiency_percent",
    "Cycle_Life_cycles",
    "Capacity_Retention_percent",
    "EIS_R_ct_before_Ohm",
    "EIS_R_ct_after_Ohm",
    "Li_Diffusion_Coefficient_cm2_s",
    "XRD_Phase_Purity",
    "Remarks",
    "Impurity_Phase_Identified",
    "Evidence",
    "Calculated_Molar_Mass",
    "Calculated_Q_M2",
    "Calculated_Li_Stoichiometry",
    "Calculated_Li_Vacancy_delta",
    "Calculated_S_config_over_R",
    "Calculated_Theoretical_Capacity_Metric",
    "Record_Classification",
]

# Explicitly map only fields supported by the current PDF extractor.
FIELD_MAP = {
    "Year": "year",
    "Composition_Formula": "composition",
    "Synthesis_Method": "synthesis_method",
    "Evidence": "evidence_quote",
}


def _is_multi_condition_retention(text: str) -> bool:
    """Check if a retention string contains multiple condition measurements."""
    lower = text.lower()
    if "," in text or ";" in text:
        return True
    if text.count("%") > 1:
        return True
    if "cycle" in lower or " c" in lower or "@" in text or "/" in text:
        return True
    if "(" in text and ")" in text:
        return True
    return False

NUMERIC_COLUMNS = {
    "Year",
    "Mn_Ratio",
    "Fe_Ratio",
    "Dopant_Count",
    "Dopant_Molar_Ratio",
    "Dopant_x_per_fu",
    "Carbon_wt_percent",
    "Calcination_Temp_1_C",
    "Calcination_Time_1_h",
    "Discharge_Capacity_0_05C_mAh_g",
    "Discharge_Capacity_0_1C_mAh_g",
    "Discharge_Capacity_1C_mAh_g",
    "Discharge_Capacity_2C_mAh_g",
    "Discharge_Capacity_5C_mAh_g",
    "Initial_Coulombic_Efficiency_percent",
    "Cycle_Life_cycles",
    "Capacity_Retention_percent",
    "EIS_R_ct_before_Ohm",
    "EIS_R_ct_after_Ohm",
    "Li_Diffusion_Coefficient_cm2_s",
    "Calculated_Molar_Mass",
    "Calculated_Q_M2",
    "Calculated_Li_Stoichiometry",
    "Calculated_Li_Vacancy_delta",
    "Calculated_S_config_over_R",
    "Calculated_Theoretical_Capacity_Metric",
}


def _clean_text(value: Any) -> str | None:
    """Return clean text or None for missing values."""
    if value is None:
        return None

    text = str(value).strip()

    if not text or text.lower() in {"nan", "none", "n/a", "unknown"}:
        return None

    return text


def _numeric_value(value: Any) -> float | None:
    """Convert a simple numeric value without guessing units or meaning."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        return number if pd.notna(number) else None

    text = str(value).strip()

    if not text:
        return None

    # Do not silently strip units, ranges, or other scientific notation.
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None

    return number if pd.notna(number) else None


def _load_master_csv() -> pd.DataFrame:
    """Load the existing dataset and verify its schema."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Master literature CSV not found: {CSV_PATH}"
        )

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "Master CSV columns do not match the expected 41-column schema. "
            "No changes were made."
        )

    return df


def _make_candidate(review: dict, master: pd.DataFrame) -> tuple[dict, list[str]]:
    """Convert one approved review into a candidate row."""
    record = review.get("extracted_data") or {}
    row = {column: None for column in EXPECTED_COLUMNS}
    errors = []

    for destination, source in FIELD_MAP.items():
        value = record.get(source)

        if destination in NUMERIC_COLUMNS:
            row[destination] = _numeric_value(value)
            if _clean_text(value) is not None and row[destination] is None:
                errors.append(
                    f"{destination} is not a plain numeric value: {value!r}"
                )
        else:
            row[destination] = _clean_text(value)

    # Source and page provenance.
    source_pdf = _clean_text(review.get("source_pdf"))
    page = review.get("page_number") or record.get("page")

    row["Source_PDF"] = source_pdf
    row["Remarks"] = (
        f"Imported from approved PDF review ID {review.get('id')}; "
        f"page {page if page is not None else 'unknown'}"
    )

    # Capacity retention handling:
    # Scientific literature tables often report multiple retention values under
    # different cycling/rate conditions (e.g., '89.45% (500 cycles, 0.1 C), ...').
    # Multi-condition retention must never be collapsed, averaged, or guessed into a
    # single numeric column. It is preserved in the review record and candidate remarks.
    raw_retention = _clean_text(record.get("capacity_retention"))
    benchmark_ret_val = record.get("benchmark_retention_percent")
    benchmark_cycles_val = record.get("benchmark_cycle_count")
    benchmark_crate_val = _clean_text(record.get("benchmark_c_rate"))
    retention_verified = bool(record.get("retention_condition_verified", False))

    if benchmark_ret_val is not None and str(benchmark_ret_val).strip():
        parsed_bm_ret = _numeric_value(benchmark_ret_val)
        if parsed_bm_ret is None:
            errors.append(
                f"Benchmark retention is not a valid numeric value: {benchmark_ret_val!r}"
            )
        elif not (0.0 <= parsed_bm_ret <= 110.0):
            errors.append(
                f"Benchmark retention {parsed_bm_ret}% is outside physically valid bounds [0.0, 110.0]."
            )
        elif raw_retention and _is_multi_condition_retention(raw_retention) and not retention_verified:
            errors.append(
                "Benchmark cycling condition must be explicitly verified before export."
            )
        else:
            row["Capacity_Retention_percent"] = parsed_bm_ret
            parsed_cycles = _numeric_value(benchmark_cycles_val)
            if parsed_cycles is not None:
                row["Cycle_Life_cycles"] = parsed_cycles
            bm_note = (
                f"Benchmark condition: {parsed_bm_ret}% "
                f"({benchmark_cycles_val or '?'} cycles, {benchmark_crate_val or '?'})"
            )
            orig_note = f"All extracted conditions: {raw_retention}" if raw_retention else ""
            row["Remarks"] = f"{row['Remarks']}; {bm_note}" + (f"; {orig_note}" if orig_note else "")
    elif raw_retention is not None:
        numeric_retention = _numeric_value(raw_retention)
        if numeric_retention is not None:
            row["Capacity_Retention_percent"] = numeric_retention
        elif _is_multi_condition_retention(raw_retention):
            row["Capacity_Retention_percent"] = None
            row["Remarks"] = (
                f"{row['Remarks']}; Extracted retention: {raw_retention}"
            )
            errors.append(
                f"Capacity retention contains multiple condition measurements and is "
                f"retained for manual review rather than mapped to a single numeric value: "
                f"{raw_retention!r}"
            )
        else:
            row["Capacity_Retention_percent"] = None
            errors.append(
                f"Capacity_Retention_percent is not a plain numeric value: {raw_retention!r}"
            )

    # Defense-in-depth: Immediately block test-contaminated records from export.
    if record.get("is_test_contaminated"):
        errors.append(
            "Record contains test data contamination and is permanently blocked from export."
        )

    # Require an identifiable composition and source.
    if not row["Composition_Formula"]:
        errors.append("Missing composition.")

    if not source_pdf:
        errors.append("Missing source PDF.")

    if not row["Evidence"]:
        errors.append("Missing evidence quote.")

    # Verified Paper & Sample Identity from reviewer or extraction:
    verified_paper_id = _clean_text(
        record.get("verified_paper_id") or record.get("Paper_ID")
    )
    verified_sample_id = _clean_text(
        record.get("verified_sample_id") or record.get("Sample_ID")
    )
    verified_doi = _clean_text(
        record.get("verified_doi")
        or record.get("doi")
        or record.get("DOI")
    )
    verified_title = _clean_text(
        record.get("verified_paper_title")
        or record.get("paper_title")
        or record.get("Paper_Title")
    )

    if not verified_paper_id:
        errors.append(
            "Paper_ID has not been reliably resolved. "
            "Link this record to its paper before export."
        )
    else:
        row["Paper_ID"] = verified_paper_id

    if not verified_sample_id:
        errors.append(
            "Sample_ID has not been reliably resolved. "
            "Link this record to its specific sample before export."
        )
    else:
        existing_sample_ids = set(
            master["Sample_ID"].dropna().astype(str).str.strip()
        )
        if verified_sample_id in existing_sample_ids:
            errors.append(
                f"Sample_ID already exists in master dataset: '{verified_sample_id}'. "
                f"Duplicate samples are prohibited."
            )
        else:
            row["Sample_ID"] = verified_sample_id

    if verified_doi:
        row["DOI"] = verified_doi
    if verified_title:
        row["Paper_Title"] = verified_title

    # Rate-specific discharge capacity values:
    capacity_rate_fields = [
        ("Discharge_Capacity_0_05C_mAh_g", "verified_capacity_0_05c"),
        ("Discharge_Capacity_0_1C_mAh_g", "verified_capacity_0_1c"),
        ("Discharge_Capacity_1C_mAh_g", "verified_capacity_1c"),
        ("Discharge_Capacity_2C_mAh_g", "verified_capacity_2c"),
        ("Discharge_Capacity_5C_mAh_g", "verified_capacity_5c"),
    ]
    for col_name, field_key in capacity_rate_fields:
        raw_val = record.get(field_key) or record.get(col_name)
        if raw_val is not None and str(raw_val).strip():
            num_val = _numeric_value(raw_val)
            if num_val is None:
                errors.append(f"{col_name} is not a plain numeric value: {raw_val!r}")
            elif not (5.0 <= num_val <= 220.0):
                errors.append(f"{col_name} value {num_val} mAh/g is outside valid range [5.0, 220.0].")
            else:
                row[col_name] = num_val
        else:
            row[col_name] = None

    # Derive chemistry metrics through project chemistry engine if formula is present:
    if row["Composition_Formula"]:
        try:
            from literature.parser import parse_composition
            from chemistry.entropy import calculate_configurational_entropy
            from chemistry.capacity import calculate_capacity_metrics

            parsed = parse_composition(row["Composition_Formula"])
            m2 = parsed.get("M2", {})
            mn_r = m2.get("Mn", 0.0)
            fe_r = m2.get("Fe", 0.0)
            dopants = [
                {"symbol": k, "fraction": v}
                for k, v in m2.items()
                if k not in ("Mn", "Fe")
            ]
            if row["Mn_Ratio"] is None and mn_r > 0:
                row["Mn_Ratio"] = mn_r
            if row["Fe_Ratio"] is None and fe_r > 0:
                row["Fe_Ratio"] = fe_r
            if row["Dopant_Count"] is None:
                row["Dopant_Count"] = len(dopants)
            if dopants:
                row["Dopant_Element"] = ";".join(d["symbol"] for d in dopants)
                row["Dopant_Molar_Ratio"] = sum(d["fraction"] for d in dopants)
            else:
                row["Dopant_Element"] = "None/Undoped"
                row["Dopant_Molar_Ratio"] = 0.0

            ent = calculate_configurational_entropy(mn_r, fe_r, dopants)
            row["Calculated_S_config_over_R"] = round(ent.s_config_over_r, 4)
            m_mass = parsed.get("molar_mass", 157.7)
            row["Calculated_Molar_Mass"] = round(m_mass, 4)
            row["Calculated_Q_M2"] = 2.0
            row["Calculated_Li_Stoichiometry"] = 1.0
            row["Calculated_Li_Vacancy_delta"] = 0.0
            cap_res = calculate_capacity_metrics(1.0, m_mass)
            row["Calculated_Theoretical_Capacity_Metric"] = round(
                cap_res.formula_calculated_capacity_metric, 2
            )
        except Exception:
            pass

    row["Record_Classification"] = CLASSIFICATION
    return row, errors


def preview_approved_exports() -> dict:
    """
    Validate approved reviews without modifying any files.

    Returns summary counts and validation errors.
    """
    master = _load_master_csv()
    approved = list_reviews(status="approved")

    results = []
    for review in approved:
        row, errors = _make_candidate(review, master)
        results.append(
            {
                "review_id": review.get("id"),
                "source_pdf": review.get("source_pdf"),
                "page_number": review.get("page_number"),
                "composition": row.get("Composition_Formula"),
                "errors": errors,
            }
        )

    return {
        "master_records": len(master),
        "approved_reviews": len(approved),
        "exportable_records": sum(not item["errors"] for item in results),
        "blocked_records": sum(bool(item["errors"]) for item in results),
        "records": results,
    }


def export_approved_reviews(*, dry_run: bool = True) -> dict:
    """
    Export eligible approved reviews.

    Dry-run is enabled by default. The current PDF extraction schema does
    not provide enough information to assign unique sample IDs and paper
    IDs safely, so incomplete records are blocked.
    """
    master = _load_master_csv()
    approved = list_reviews(status="approved")

    if not approved:
        return {
            "status": "nothing_to_export",
            "master_records": len(master),
            "approved_reviews": 0,
            "added_records": 0,
        }

    existing_ids = set(
        master["Sample_ID"].dropna().astype(str).str.strip()
    )
    new_rows = []
    blocked = []

    for review in approved:
        row, errors = _make_candidate(review, master)

        if not errors:
            sample_id = _clean_text(row.get("Sample_ID"))

            if not sample_id:
                errors.append("Missing Sample_ID.")
            elif sample_id in existing_ids:
                errors.append(f"Sample_ID already exists: {sample_id}")
            else:
                existing_ids.add(sample_id)
                new_rows.append(row)

        if errors:
            blocked.append(
                {"review_id": review.get("id"), "errors": errors}
            )

    if dry_run:
        return {
            "status": "dry_run",
            "master_records": len(master),
            "approved_reviews": len(approved),
            "eligible_records": len(new_rows),
            "blocked_records": len(blocked),
            "blocked_details": blocked,
            "csv_modified": False,
        }

    if not new_rows:
        return {
            "status": "no_eligible_records",
            "master_records": len(master),
            "approved_reviews": len(approved),
            "blocked_records": len(blocked),
            "blocked_details": blocked,
            "csv_modified": False,
        }

    # Create a timestamped backup before writing.
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"literature_reference_{timestamp}.csv"
    shutil.copy2(CSV_PATH, backup_path)

    new_df = pd.DataFrame(new_rows, columns=EXPECTED_COLUMNS)
    combined = pd.concat([master, new_df], ignore_index=True)
    combined.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    return {
        "status": "exported",
        "original_records": len(master),
        "added_records": len(new_df),
        "total_records": len(combined),
        "backup_path": str(backup_path),
        "blocked_records": len(blocked),
        "blocked_details": blocked,
    }


if __name__ == "__main__":
    import json

    # Safe by default: validates and prints a preview only.
    print(json.dumps(preview_approved_exports(), indent=2))

