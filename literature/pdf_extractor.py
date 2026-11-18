"""Extract text and LMFP literature data from research-paper PDFs."""

import re
from dataclasses import asdict
from typing import Any
import fitz  # PyMuPDF

from literature.composition_parser import parse_lmfp_composition
from literature.ollama_extractor import parse_lmfp_doping_table
from literature.property_extractor import extract_properties_from_document
from literature.section_parser import (
    segment_document_pages,
    SectionType,
    is_experimental_section,
    is_background_section,
    is_non_scientific_section,
)


KNOWN_DOPANTS = [
    "Mg", "Ti", "V", "Cr", "Co", "Ni", "Cu", "Zn", "Zr", "Nb", "Mo",
    "Al", "Ga", "In", "Sn", "Y", "F", "Cl", "B", "S", "N", "Na", "Ca", "W"
]

SYNTHESIS_ROUTES = [
    ("sol-gel", "Sol-gel"),
    ("sol gel", "Sol-gel"),
    ("hydrothermal", "Hydrothermal"),
    ("solvothermal", "Solvothermal"),
    ("solid-state", "Solid-state"),
    ("solid state", "Solid-state"),
    ("coprecipitation", "Co-precipitation"),
    ("co-precipitation", "Co-precipitation"),
    ("spray pyrolysis", "Spray pyrolysis"),
    ("ball milling", "Ball milling"),
    ("combustion", "Combustion"),
]


def extract_pdf_pages(pdf_bytes: bytes) -> list[dict]:
    """Extract text from a PDF and return one entry per page."""
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")

    pages = []

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.needs_pass:
                raise ValueError("This PDF is password-protected.")

            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text").strip()

                pages.append({
                    "page": page_number,
                    "text": text,
                })

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "Could not read this PDF. Please check that it is a valid PDF."
        ) from exc

    if not any(page["text"] for page in pages):
        raise ValueError(
            "No selectable text was found. Scanned PDFs need OCR support."
        )

    return pages


def _extract_capacity_at_rate(text: str, rate_str: str) -> float | None:
    """Extract discharge capacity (mAh/g) for a specific C-rate."""
    escaped_rate = re.escape(rate_str)
    # Pattern 1: '163.8 mAh/g at 0.1 C' or '163.8 (0.1 C)'
    p1 = rf"(\d+(?:\.\d+)?)\s*(?:mAh\s*[\/\-]?\s*g(?:-1)?)?\s*(?:\(|at|@)?\s*{escaped_rate}\s*C"
    # Pattern 2: 'at 0.1 C: 163.8 mAh/g' or 'at 0.1 C, 163.8 mAh/g'
    p2 = rf"(?:at|@)\s*{escaped_rate}\s*C[^\n.]{{0,30}}?(\d+(?:\.\d+)?)\s*mAh"

    for pattern in (p1, p2):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 20.0 <= val <= 250.0:
                    return round(val, 2)
            except (ValueError, TypeError):
                continue
    return None


def _extract_retention(text: str) -> tuple[float | None, int | None, float | None]:
    """Extract capacity retention percent, cycle count, and test C-rate."""
    # Pattern A: 'retention of 95.8% after 200 cycles at 1 C' or '100.0% (100 cycles, 1 C)'
    mA = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:capacity\s+retention|retention)?[^\n.]{0,35}?(?:after|\()\s*(\d+)\s*cycles?(?:[,\s]+(?:at|@)?\s*(\d+(?:\.\d+)?)\s*C)?",
        text,
        re.IGNORECASE,
    )
    if mA:
        try:
            pct = float(mA.group(1))
            cycles = int(mA.group(2))
            crate = float(mA.group(3)) if mA.group(3) else None
            return round(pct, 2), cycles, crate
        except (ValueError, TypeError):
            pass

    # Pattern B: 'after 200 cycles at 1C, retention was 94%'
    mB = re.search(
        r"(?:after|\()\s*(\d+)\s*cycles?(?:[,\s]+(?:at|@)?\s*(\d+(?:\.\d+)?)\s*C)?[^\n.]{0,35}?(\d+(?:\.\d+)?)\s*%",
        text,
        re.IGNORECASE,
    )
    if mB:
        try:
            cycles = int(mB.group(1))
            crate = float(mB.group(2)) if mB.group(2) else None
            pct = float(mB.group(3))
            return round(pct, 2), cycles, crate
        except (ValueError, TypeError):
            pass

    # Pattern C: general percentage near retention keyword
    mC = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:capacity\s+retention|retention)",
        text,
        re.IGNORECASE,
    )
    if mC:
        try:
            pct = float(mC.group(1))
            return round(pct, 2), None, None
        except (ValueError, TypeError):
            pass

    return None, None, None


def _extract_synthesis_method(text: str) -> str | None:
    """Find reported synthesis route in text."""
    lower = text.lower()
    for needle, clean_name in SYNTHESIS_ROUTES:
        if needle in lower:
            return clean_name
    return None


def _extract_dopant_element(text: str, formula: str) -> str | None:
    """Find dopant elements mentioned in formula or nearby text without confusing host atoms."""
    # Strip host atoms: Li, Mn, Fe, P, O, and carbon coating /C
    cleaned = re.sub(r"Li|Mn|Fe|PO4?|/C|/c|[0-9._\(\)\[\]\s-]", "", formula)
    for dop in sorted(KNOWN_DOPANTS, key=len, reverse=True):
        if dop == cleaned or dop in cleaned:
            return dop

    # Check for explicit 'X-doped' or 'doped with X'
    dop_match = re.search(
        r"\b(?:doped with|co-doped with|doping of|doped)\s+([A-Z][a-z]?)\b",
        text,
        re.IGNORECASE,
    )
    if dop_match and dop_match.group(1) in KNOWN_DOPANTS:
        return dop_match.group(1)

    return None


def parse_text_lmfp_records(page_text: str, page_number: int) -> list[dict]:
    """Extract candidate LMFP records from narrative paper text."""
    records = []

    # Match LMFP stoichiometry formulas: e.g. LiMn0.7Fe0.3PO4, LiMn0.8Fe0.2PO4/C, LiFe0.6Mn0.4PO4
    formula_pattern = re.compile(
        r"\bLi[A-Za-z0-9_.]*(?:Mn[0-9.]*Fe[0-9.]*|Fe[0-9.]*Mn[0-9.]*)[A-Za-z0-9_.]*PO4(?:\/[A-Za-z0-9_]+)?\b"
    )

    # Split page into paragraphs or blocks, and unwrap line breaks within paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page_text) if p.strip()]
    if not paragraphs:
        paragraphs = [page_text.strip()]
    paragraphs = [re.sub(r"\s*\n\s*", " ", p) for p in paragraphs]

    seen_formulas = set()

    for para in paragraphs:
        matches = list(formula_pattern.finditer(para))
        if not matches:
            continue

        for match in matches:
            formula = match.group(0).strip()
            # Clean trailing punctuation
            formula = re.sub(r"[,;.:)]+$", "", formula)

            if formula in seen_formulas:
                continue

            seen_formulas.add(formula)

            # Context window around this paragraph
            context = para

            cap_01 = _extract_capacity_at_rate(context, "0.1")
            cap_1 = _extract_capacity_at_rate(context, "1")
            cap_5 = _extract_capacity_at_rate(context, "5")
            pct, cycles, crate = _extract_retention(context)
            synthesis = _extract_synthesis_method(context)
            dopant = _extract_dopant_element(context, formula)

            # Look for reference: [12] or (12)
            ref_match = re.search(r"\[(\d+)\]", context)
            ref_str = ref_match.group(0) if ref_match else None

            # Look for publication year
            year_match = re.search(r"\b(201\d|202\d)\b", context)
            year_str = year_match.group(1) if year_match else None

            rate_cap_parts = []
            if cap_01:
                rate_cap_parts.append(f"{cap_01} (0.1 C)")
            if cap_1:
                rate_cap_parts.append(f"{cap_1} (1 C)")
            if cap_5:
                rate_cap_parts.append(f"{cap_5} (5 C)")
            rate_capability = ", ".join(rate_cap_parts) if rate_cap_parts else None

            retention_parts = []
            if pct:
                ret_str = f"{pct}%"
                if cycles and crate:
                    ret_str += f" ({cycles} cycles, {crate} C)"
                elif cycles:
                    ret_str += f" ({cycles} cycles)"
                retention_parts.append(ret_str)
            capacity_retention = ", ".join(retention_parts) if retention_parts else None

            missing_fields = []
            if not cap_01 and not cap_1:
                missing_fields.append("discharge_capacity")
            if not pct:
                missing_fields.append("capacity_retention")
            if not ref_str:
                missing_fields.append("reference")

            # Clean evidence quote
            evidence = context.replace("\n", " ").strip()
            if len(evidence) > 350:
                evidence = evidence[:347] + "..."

            records.append({
                "page": page_number,
                "composition": formula,
                "year": year_str,
                "synthesis_method": synthesis,
                "doping_element": dopant,
                "doping_agent": None,
                "rate_capability": rate_capability,
                "discharge_capacity_0_1c": cap_01,
                "discharge_capacity_1c": cap_1,
                "discharge_capacity_5c": cap_5,
                "capacity_retention": capacity_retention,
                "capacity_retention_percent": pct,
                "retention_cycles": cycles,
                "retention_crate": crate,
                "reference": ref_str,
                "evidence_quote": evidence,
                "missing_fields": missing_fields,
                "extraction_type": "text",
            })

    return records


def extract_lmfp_records_from_pages(pages: list[dict], source_pdf: str = "") -> dict:
    """Extract structured LMFP records from document pages using section zoning, tables and text parsing."""
    doc_struct = segment_document_pages(pages, source_pdf=source_pdf)

    keywords = ("capacity", "retention", "synthesis", "doping", "calcination", "discharge", "electrochemical", "lmfp", "limn")

    candidate_pages = []
    for p in pages:
        page_num = p["page"]
        lower_txt = p["text"].lower()
        matched = [k for k in keywords if k in lower_txt]
        page_sections = sorted(list({
            b.section_type.value for b in doc_struct.blocks if b.page_number == page_num
        }))
        if matched:
            snippet = p["text"][:300].replace("\n", " ").strip()
            candidate_pages.append({
                "page": page_num,
                "snippet": snippet,
                "matched_keywords": matched,
                "detected_sections": page_sections,
            })

    all_records = []
    background_mentions = []
    seen_compositions = set()

    for p in pages:
        page_num = p["page"]
        text = p["text"]
        if not text.strip():
            continue

        # 1. Attempt structured doping table parsing
        table_res = parse_lmfp_doping_table(text, page_num)
        table_rows = table_res.get("table_rows", [])

        if table_rows:
            for row in table_rows:
                comp = row.get("composition")
                if not comp:
                    continue

                rate_cap = row.get("rate_capability") or ""
                cap_01 = _extract_capacity_at_rate(rate_cap, "0.1")
                cap_1 = _extract_capacity_at_rate(rate_cap, "1")
                cap_5 = _extract_capacity_at_rate(rate_cap, "5")

                ret_str = row.get("capacity_retention") or ""
                pct, cycles, crate = _extract_retention(ret_str)

                missing_fields = []
                if not cap_01 and not cap_1:
                    missing_fields.append("discharge_capacity")
                if not pct:
                    missing_fields.append("capacity_retention")
                if not row.get("reference"):
                    missing_fields.append("reference")

                record = {
                    "page": page_num,
                    "composition": comp,
                    "year": row.get("year"),
                    "synthesis_method": row.get("synthesis_method"),
                    "doping_element": row.get("doping_element"),
                    "doping_agent": row.get("doping_agent"),
                    "rate_capability": rate_cap,
                    "discharge_capacity_0_1c": cap_01,
                    "discharge_capacity_1c": cap_1,
                    "discharge_capacity_5c": cap_5,
                    "capacity_retention": ret_str,
                    "capacity_retention_percent": pct,
                    "retention_cycles": cycles,
                    "retention_crate": crate,
                    "active_mass_loading": row.get("active_mass_loading"),
                    "voltage_window": row.get("voltage_window"),
                    "reference": row.get("reference"),
                    "evidence_quote": row.get("evidence_quote") or "",
                    "missing_fields": missing_fields,
                    "extraction_type": "table",
                    "section_type": SectionType.TABLE.value,
                    "section_label": "Table",
                    "is_experimental": True,
                    "is_background": False,
                }
                key = (comp, page_num, row.get("reference"))
                if key not in seen_compositions:
                    seen_compositions.add(key)
                    all_records.append(record)

    # 2. Section-aware text block processing
    formula_regex = re.compile(
        r"\bLi[A-Za-z0-9_.]*(?:Mn[0-9.]*Fe[0-9.]*|Fe[0-9.]*Mn[0-9.]*)[A-Za-z0-9_.]*PO4(?:\/[A-Za-z0-9_]+)?\b"
    )

    for block in doc_struct.blocks:
        # Strictly skip Reference sections (do not create sample records from citations)
        if block.section_type in {SectionType.REFERENCES, SectionType.ACKNOWLEDGEMENTS, SectionType.CORRIGENDUM}:
            continue

        # If mentioned in Introduction or Abstract: capture as background literature mention
        if block.section_type in {SectionType.INTRODUCTION, SectionType.ABSTRACT}:
            matches = list(formula_regex.finditer(block.text))
            for m in matches:
                formula = m.group(0).strip().rstrip(".,;:)")
                background_mentions.append({
                    "composition": formula,
                    "page": block.page_number,
                    "section_type": block.section_type.value,
                    "section_label": block.section_label,
                    "evidence_quote": block.text[:300].strip(),
                    "is_background": True,
                })
            continue

        # Experimental, Results & Discussion, Figure captions, and unclassified blocks
        text_records = parse_text_lmfp_records(block.text, block.page_number)
        for tr in text_records:
            comp = tr.get("composition")
            key = (comp, block.page_number, tr.get("reference"))
            if key not in seen_compositions:
                seen_compositions.add(key)
                tr["section_type"] = block.section_type.value
                tr["section_label"] = block.section_label
                tr["table_id"] = block.table_id
                tr["figure_id"] = block.figure_id
                tr["is_experimental"] = block.is_experimental
                tr["is_background"] = False
                all_records.append(tr)

    # -----------------------------------------------------------------------
    # Stage 3: Scientific Property, Synthesis & Characterization Extraction
    # -----------------------------------------------------------------------
    paper_properties = extract_properties_from_document(
        doc_struct=doc_struct,
        source_pdf=source_pdf,
    )

    # Count primary experimental compositions in this document
    exp_comps = list({r.get("composition") for r in all_records if r.get("is_experimental") and r.get("composition")})

    # Enrich existing records with Stage 2 composition validation & Stage 3 measurements
    for rec in all_records:
        rec_comp = rec.get("composition", "")
        rec_page = rec.get("page")

        # Stage 2: Composition parsing & validation
        try:
            parsed_comp = parse_lmfp_composition(rec_comp)
            rec["parsed_composition"] = asdict(parsed_comp)
        except Exception:
            pass

        # Match Stage 3 structured measurements by page and sample/composition
        matched_meas = []
        for m in paper_properties.measurements:
            if m.page_number == rec_page:
                if not m.sample_label or m.sample_label in rec_comp or rec_comp in (m.sample_label or ""):
                    matched_meas.append(m)
            elif m.sample_label and m.sample_label == rec_comp:
                matched_meas.append(m)
            elif not m.sample_label and len(exp_comps) == 1 and exp_comps[0] == rec_comp:
                # Single-composition paper: Results & Discussion measurements unambiguously belong to this composition
                matched_meas.append(m)

        rec["structured_measurements"] = [asdict(m) for m in matched_meas]

        # Match synthesis and characterization profiles
        synth_match = [
            asdict(s) for s in paper_properties.synthesis_profiles
            if s.source_page == rec_page or (s.sample_label and s.sample_label in rec_comp)
        ]
        char_match = [
            asdict(ch) for ch in paper_properties.characterization_profiles
            if ch.source_page == rec_page or (ch.sample_label and ch.sample_label in rec_comp)
        ]

        if synth_match:
            rec["synthesis_profile"] = synth_match[0]
            if not rec.get("synthesis_method") and synth_match[0].get("route"):
                rec["synthesis_method"] = synth_match[0]["route"]
        if char_match:
            rec["characterization_profile"] = char_match[0]

        # Fill missing capacity or retention if verified by Stage 3
        if not rec.get("discharge_capacity_0_1c"):
            cap_01_m = next((m for m in matched_meas if m.measurement_type == "discharge_capacity" and m.conditions.get("c_rate") == 0.1), None)
            if cap_01_m:
                rec["discharge_capacity_0_1c"] = cap_01_m.normalized_value
        if not rec.get("discharge_capacity_1c"):
            cap_1_m = next((m for m in matched_meas if m.measurement_type == "discharge_capacity" and m.conditions.get("c_rate") == 1.0), None)
            if cap_1_m:
                rec["discharge_capacity_1c"] = cap_1_m.normalized_value

        if not rec.get("capacity_retention_percent"):
            ret_m = next((m for m in matched_meas if m.measurement_type == "capacity_retention"), None)
            if ret_m:
                rec["capacity_retention_percent"] = ret_m.normalized_value
                rec["retention_cycles"] = ret_m.conditions.get("cycle_count")
                rec["retention_crate"] = ret_m.conditions.get("c_rate")
                rec["capacity_retention"] = f"{ret_m.normalized_value}% ({ret_m.conditions.get('cycle_count')} cycles, {ret_m.conditions.get('c_rate')} C)"

        # Recalculate missing fields based on verified values
        missing = []
        if not rec.get("discharge_capacity_0_1c") and not rec.get("discharge_capacity_1c"):
            missing.append("discharge_capacity")
        if not rec.get("capacity_retention_percent"):
            missing.append("capacity_retention")
        if not rec.get("reference"):
            missing.append("reference")
        rec["missing_fields"] = missing

    # Identify samples that were only captured as named experimental samples (e.g. SD_NO3, SD_SO4)
    # Strictly exclude Introduction and Abstract mentions from generating primary experimental sample records
    named_samples = set()
    for m in paper_properties.measurements:
        if m.section_type in {SectionType.INTRODUCTION.value, SectionType.ABSTRACT.value}:
            continue
        if m.sample_label and not any(r.get("composition") == m.sample_label for r in all_records):
            named_samples.add((m.sample_label, m.page_number))

    for sample_label, page_num in sorted(named_samples):
        sample_meas = [
            m for m in paper_properties.measurements
            if m.sample_label == sample_label and m.page_number == page_num
        ]
        if not sample_meas:
            continue

        cap_01 = next((m.normalized_value for m in sample_meas if m.measurement_type == "discharge_capacity" and m.conditions.get("c_rate") == 0.1), None)
        cap_1 = next((m.normalized_value for m in sample_meas if m.measurement_type == "discharge_capacity" and m.conditions.get("c_rate") == 1.0), None)
        cap_5 = next((m.normalized_value for m in sample_meas if m.measurement_type == "discharge_capacity" and m.conditions.get("c_rate") == 5.0), None)
        ret_m = next((m for m in sample_meas if m.measurement_type == "capacity_retention"), None)

        rate_parts = [
            f"{m.normalized_value} ({m.conditions.get('c_rate')} C)"
            for m in sample_meas if m.measurement_type == "discharge_capacity" and m.conditions.get("c_rate") is not None
        ]

        missing = []
        if not cap_01 and not cap_1:
            missing.append("discharge_capacity")
        if not ret_m:
            missing.append("capacity_retention")
        missing.append("reference")

        synth_m = next((asdict(s) for s in paper_properties.synthesis_profiles if s.sample_label == sample_label or s.source_page == page_num), None)
        char_m = next((asdict(ch) for ch in paper_properties.characterization_profiles if ch.sample_label == sample_label or ch.source_page == page_num), None)

        all_records.append({
            "page": page_num,
            "composition": sample_label,
            "year": None,
            "synthesis_method": synth_m.get("route") if synth_m else None,
            "doping_element": None,
            "doping_agent": None,
            "rate_capability": ", ".join(rate_parts) if rate_parts else None,
            "discharge_capacity_0_1c": cap_01,
            "discharge_capacity_1c": cap_1,
            "discharge_capacity_5c": cap_5,
            "capacity_retention": f"{ret_m.normalized_value}% ({ret_m.conditions.get('cycle_count')} cycles, {ret_m.conditions.get('c_rate')} C)" if ret_m else None,
            "capacity_retention_percent": ret_m.normalized_value if ret_m else None,
            "retention_cycles": ret_m.conditions.get("cycle_count") if ret_m else None,
            "retention_crate": ret_m.conditions.get("c_rate") if ret_m else None,
            "voltage_window": next((m.conditions.get("voltage_window") for m in sample_meas if m.conditions.get("voltage_window")), None),
            "reference": None,
            "evidence_quote": sample_meas[0].evidence_quote,
            "missing_fields": missing,
            "extraction_type": "property_engine",
            "section_type": sample_meas[0].section_type,
            "section_label": sample_meas[0].section_type.title(),
            "is_experimental": True,
            "is_background": False,
            "structured_measurements": [asdict(m) for m in sample_meas],
            "synthesis_profile": synth_m,
            "characterization_profile": char_m,
        })

    # Determine status and warnings
    warnings = []
    if not all_records:
        status = "no_records_found"
        warnings.append(
            "No LMFP compositions or electrochemical performance records were detected in the document text."
        )
        message = "No LMFP records extracted. Verify that this paper reports LiMnxFe1-xPO4 materials and contains selectable text."
        suggested_next_action = "Check if the uploaded PDF contains selectable text (not scanned images) and explicitly reports LMFP compositions or doping tables."
    else:
        has_missing = any(len(r.get("missing_fields", [])) > 0 for r in all_records)
        if has_missing:
            status = "partial_extraction"
            missing_items = [
                f"{r['composition']} (p. {r['page']}): missing {', '.join(r['missing_fields'])}"
                for r in all_records if r.get("missing_fields")
            ]
            warnings.append(
                f"Some records have missing fields: {'; '.join(missing_items[:3])}"
            )
            message = f"Extracted {len(all_records)} LMFP records. Some fields are missing and require human reviewer confirmation."
            suggested_next_action = "Review the extracted records in the queue below. Open the Reviewer Disambiguation modal to verify DOI, sample ID, and benchmark conditions."
        else:
            status = "success"
            message = f"Successfully extracted {len(all_records)} LMFP records."
            suggested_next_action = "Review and verify extracted records in the queue below before approving for dataset export."

    # -----------------------------------------------------------------------
    # Stage 4: Sample-Centric Entity Graph Resolution & Persistence
    # -----------------------------------------------------------------------
    resolved_samples_list = []
    try:
        from literature.sample_resolver import resolve_sample_entities_from_document
        from literature.entity_store import save_paper_entity_graph, get_material_sample_graph

        paper_entity = resolve_sample_entities_from_document(
            source_pdf=source_pdf,
            paper_properties=paper_properties,
            raw_records=all_records,
            is_review_paper="review" in source_pdf.lower(),
        )
        save_paper_entity_graph(paper_entity)
        resolved_samples_list = [
            get_material_sample_graph(s.sample_id) for s in paper_entity.samples
        ]
        resolved_samples_list = [s for s in resolved_samples_list if s is not None]
    except Exception:
        # Graceful fallback if database path is isolated or locked in tests
        pass

    return {
        "status": status,
        "records": all_records,
        "candidate_pages": candidate_pages,
        "warnings": warnings,
        "message": message,
        "suggested_next_action": suggested_next_action,
        "detected_sections": doc_struct.detected_sections,
        "background_mentions": background_mentions,
        "background_mentions_count": len(background_mentions),
        "structured_measurements": [asdict(m) for m in paper_properties.measurements],
        "synthesis_profiles": [asdict(s) for s in paper_properties.synthesis_profiles],
        "characterization_profiles": [asdict(ch) for ch in paper_properties.characterization_profiles],
        "property_summary": {
            "total_measurements": len(paper_properties.measurements),
            "capacities_count": len([m for m in paper_properties.measurements if "capacity" in m.measurement_type]),
            "retentions_count": len([m for m in paper_properties.measurements if m.measurement_type == "capacity_retention"]),
            "synthesis_profiles_count": len(paper_properties.synthesis_profiles),
            "characterization_profiles_count": len(paper_properties.characterization_profiles),
        },
        "resolved_samples": resolved_samples_list,
        "resolved_samples_count": len(resolved_samples_list),
    }
