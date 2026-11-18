"""
Persistent SQLite Storage for Sample-Centric Entity Graph (Stage 4).

Stores:
- Papers (entity_papers)
- Material Samples (entity_samples)
- Compositions (entity_compositions)
- Synthesis Profiles (entity_synthesis_profiles)
- Characterization Profiles (entity_characterization_profiles)
- Property Measurements (entity_measurements)
- Evidence Records (entity_evidence)
- Secondary Citations (secondary_citations)

Strictly preserves existing `extraction_reviews` table and master dataset CSV.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from literature.entity_models import (
    CharacterizationProfileEntity,
    CompositeModificationEntity,
    CompositionEntity,
    DopantEntity,
    EvidenceRecordEntity,
    MaterialSample,
    PaperEntity,
    PropertyMeasurementEntity,
    ProvenanceType,
    ResolutionStatus,
    SecondaryCitationLink,
    SynthesisProfileEntity,
)


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "literature_review.db"
)


def init_entity_tables():
    """Create Stage 4 entity relational schema if not already present."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 1. Papers
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_papers (
                paper_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                doi TEXT,
                authors TEXT,
                year INTEGER,
                journal TEXT,
                is_review_paper INTEGER DEFAULT 0,
                source_pdf TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 2. Secondary Citations
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS secondary_citations (
                citation_id TEXT PRIMARY KEY,
                review_paper_id TEXT NOT NULL,
                citation_key TEXT NOT NULL,
                primary_paper_id TEXT,
                primary_doi TEXT,
                primary_title TEXT,
                primary_year INTEGER,
                is_verified INTEGER DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (review_paper_id) REFERENCES entity_papers(paper_id)
            )
            """
        )

        # 3. Compositions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_compositions (
                composition_id TEXT PRIMARY KEY,
                raw_formula TEXT NOT NULL,
                base_lmfp_formula TEXT NOT NULL,
                mn_ratio REAL DEFAULT 0.5,
                fe_ratio REAL DEFAULT 0.5,
                li_stoichiometry REAL DEFAULT 1.0,
                dopants_json TEXT DEFAULT '[]',
                modifications_json TEXT DEFAULT '[]',
                is_stoichiometric INTEGER DEFAULT 1,
                configurational_entropy REAL
            )
            """
        )

        # 4. Synthesis Profiles
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_synthesis_profiles (
                synthesis_profile_id TEXT PRIMARY KEY,
                method TEXT NOT NULL,
                calcination_temp_c REAL,
                calcination_time_h REAL,
                heating_rate_c_min REAL,
                atmosphere TEXT,
                precursor_salts_json TEXT DEFAULT '[]',
                solvent TEXT,
                raw_evidence TEXT,
                source_page INTEGER DEFAULT 1
            )
            """
        )

        # 5. Characterization Profiles
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_characterization_profiles (
                characterization_profile_id TEXT PRIMARY KEY,
                crystal_structure TEXT DEFAULT 'orthorhombic olivine',
                space_group TEXT DEFAULT 'Pnma',
                xrd_phase_purity TEXT,
                impurity_phases_json TEXT DEFAULT '[]',
                lattice_a_angstrom REAL,
                lattice_b_angstrom REAL,
                lattice_c_angstrom REAL,
                unit_cell_volume_angstrom3 REAL,
                particle_size_nm REAL,
                morphology TEXT,
                eis_rct_ohm REAL,
                li_diffusion_coefficient_cm2_s REAL,
                raw_evidence TEXT,
                source_page INTEGER DEFAULT 1
            )
            """
        )

        # 6. Material Samples
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_samples (
                sample_id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                sample_label TEXT NOT NULL,
                composition_id TEXT NOT NULL,
                synthesis_profile_id TEXT,
                characterization_profile_id TEXT,
                provenance_type TEXT DEFAULT 'PRIMARY_EXPERIMENTAL',
                resolution_status TEXT DEFAULT 'CONFIRMED_EXPLICIT',
                resolution_confidence REAL DEFAULT 1.0,
                resolution_notes TEXT,
                secondary_citation_id TEXT,
                is_unresolved INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES entity_papers(paper_id),
                FOREIGN KEY (composition_id) REFERENCES entity_compositions(composition_id),
                FOREIGN KEY (synthesis_profile_id) REFERENCES entity_synthesis_profiles(synthesis_profile_id),
                FOREIGN KEY (characterization_profile_id) REFERENCES entity_characterization_profiles(characterization_profile_id),
                FOREIGN KEY (secondary_citation_id) REFERENCES secondary_citations(citation_id)
            )
            """
        )

        # 7. Property Measurements
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_measurements (
                measurement_id TEXT PRIMARY KEY,
                sample_id TEXT,
                paper_id TEXT NOT NULL,
                measurement_type TEXT NOT NULL,
                reported_value TEXT,
                reported_unit TEXT,
                normalized_value REAL,
                normalized_unit TEXT,
                c_rate REAL,
                cycle_count INTEGER,
                temperature_c REAL DEFAULT 25.0,
                voltage_window_lower_v REAL,
                voltage_window_upper_v REAL,
                source_page INTEGER DEFAULT 1,
                section_type TEXT DEFAULT 'RESULTS',
                table_or_figure_ref TEXT,
                evidence_quote TEXT,
                extraction_method TEXT DEFAULT 'stage3_property_extractor',
                validation_status TEXT DEFAULT 'VERIFIED',
                FOREIGN KEY (sample_id) REFERENCES entity_samples(sample_id),
                FOREIGN KEY (paper_id) REFERENCES entity_papers(paper_id)
            )
            """
        )

        # 8. Evidence Records
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_evidence (
                evidence_id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                section_type TEXT NOT NULL,
                text_snippet TEXT NOT NULL,
                table_or_figure_ref TEXT,
                FOREIGN KEY (paper_id) REFERENCES entity_papers(paper_id)
            )
            """
        )

        # 9. Relational Dopants View (normalized access to JSON dopants)
        cursor.execute(
            """
            CREATE VIEW IF NOT EXISTS entity_dopants AS
            SELECT 
                c.composition_id,
                s.sample_id,
                s.paper_id,
                json_extract(j.value, '$.symbol') AS dopant_symbol,
                CAST(json_extract(j.value, '$.fraction') AS REAL) AS dopant_fraction,
                CAST(json_extract(j.value, '$.oxidation_state') AS INTEGER) AS oxidation_state,
                json_extract(j.value, '$.substitution_site') AS substitution_site
            FROM entity_compositions c
            JOIN entity_samples s ON c.composition_id = s.composition_id
            JOIN json_each(c.dopants_json) j
            WHERE c.dopants_json IS NOT NULL AND c.dopants_json != '[]'
            """
        )

        conn.commit()


def save_paper_entity_graph(paper: PaperEntity):
    """Persist a full PaperEntity graph including all samples and measurements."""
    init_entity_tables()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Insert or replace Paper
        cursor.execute(
            """
            INSERT OR REPLACE INTO entity_papers (
                paper_id, title, doi, authors, year, journal, is_review_paper, source_pdf
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper.paper_id,
                paper.title,
                paper.doi,
                paper.authors,
                paper.year,
                paper.journal,
                1 if paper.is_review_paper else 0,
                paper.source_pdf,
            ),
        )

        # Insert secondary citations
        for cit in paper.secondary_citations:
            cursor.execute(
                """
                INSERT OR REPLACE INTO secondary_citations (
                    citation_id, review_paper_id, citation_key, primary_paper_id,
                    primary_doi, primary_title, primary_year, is_verified, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cit.citation_id,
                    cit.review_paper_id,
                    cit.citation_key,
                    cit.primary_paper_id,
                    cit.primary_doi,
                    cit.primary_title,
                    cit.primary_year,
                    1 if cit.is_verified else 0,
                    cit.notes,
                ),
            )

        # Insert Samples and their sub-entities
        for sample in paper.samples:
            comp = sample.composition
            dopants_data = [
                {"element": d.element, "symbol": d.element, "fraction": d.molar_ratio, "site": d.substitution_site, "agent": d.precursor_agent}
                for d in comp.dopants
            ]
            mods_data = [
                {"type": m.modification_type, "source": m.carbon_source, "wt_percent": m.carbon_wt_percent}
                for m in comp.composite_modifications
            ]

            cursor.execute(
                """
                INSERT OR REPLACE INTO entity_compositions (
                    composition_id, raw_formula, base_lmfp_formula, mn_ratio, fe_ratio,
                    li_stoichiometry, dopants_json, modifications_json, is_stoichiometric, configurational_entropy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comp.composition_id,
                    comp.raw_formula,
                    comp.base_lmfp_formula,
                    comp.mn_ratio,
                    comp.fe_ratio,
                    comp.li_stoichiometry,
                    json.dumps(dopants_data),
                    json.dumps(mods_data),
                    1 if comp.is_stoichiometric else 0,
                    comp.configurational_entropy_over_r,
                ),
            )

            # Synthesis Profile
            syn_id = None
            if sample.synthesis_profile:
                syn = sample.synthesis_profile
                syn_id = syn.synthesis_profile_id
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO entity_synthesis_profiles (
                        synthesis_profile_id, method, calcination_temp_c, calcination_time_h,
                        heating_rate_c_min, atmosphere, precursor_salts_json, solvent, raw_evidence, source_page
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        syn.synthesis_profile_id,
                        syn.method,
                        syn.calcination_temp_c,
                        syn.calcination_time_h,
                        syn.heating_rate_c_min,
                        syn.atmosphere,
                        json.dumps(syn.precursor_salts),
                        syn.solvent,
                        syn.raw_evidence,
                        syn.source_page,
                    ),
                )

            # Characterization Profile
            char_id = None
            if sample.characterization_profile:
                ch = sample.characterization_profile
                char_id = ch.characterization_profile_id
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO entity_characterization_profiles (
                        characterization_profile_id, crystal_structure, space_group, xrd_phase_purity,
                        impurity_phases_json, lattice_a_angstrom, lattice_b_angstrom, lattice_c_angstrom,
                        unit_cell_volume_angstrom3, particle_size_nm, morphology, eis_rct_ohm,
                        li_diffusion_coefficient_cm2_s, raw_evidence, source_page
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ch.characterization_profile_id,
                        ch.crystal_structure,
                        ch.space_group,
                        ch.xrd_phase_purity,
                        json.dumps(ch.impurity_phases),
                        ch.lattice_a_angstrom,
                        ch.lattice_b_angstrom,
                        ch.lattice_c_angstrom,
                        ch.unit_cell_volume_angstrom3,
                        ch.particle_size_nm,
                        ch.morphology,
                        ch.eis_rct_ohm,
                        ch.li_diffusion_coefficient_cm2_s,
                        ch.raw_evidence,
                        ch.source_page,
                    ),
                )

            # Material Sample
            sec_cit_id = sample.secondary_citation.citation_id if sample.secondary_citation else None
            cursor.execute(
                """
                INSERT OR REPLACE INTO entity_samples (
                    sample_id, paper_id, sample_label, composition_id, synthesis_profile_id,
                    characterization_profile_id, provenance_type, resolution_status,
                    resolution_confidence, resolution_notes, secondary_citation_id, is_unresolved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample.sample_id,
                    sample.paper_id,
                    sample.sample_label,
                    comp.composition_id,
                    syn_id,
                    char_id,
                    sample.provenance_type.value,
                    sample.resolution_status.value,
                    sample.resolution_confidence,
                    sample.resolution_notes,
                    sec_cit_id,
                    1 if sample.is_unresolved else 0,
                ),
            )

            # Property Measurements
            for m in sample.measurements:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO entity_measurements (
                        measurement_id, sample_id, paper_id, measurement_type, reported_value,
                        reported_unit, normalized_value, normalized_unit, c_rate, cycle_count,
                        temperature_c, voltage_window_lower_v, voltage_window_upper_v, source_page,
                        section_type, table_or_figure_ref, evidence_quote, extraction_method, validation_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        m.measurement_id,
                        sample.sample_id,
                        m.paper_id,
                        m.measurement_type,
                        str(m.reported_value),
                        m.reported_unit,
                        m.normalized_value,
                        m.normalized_unit,
                        m.c_rate,
                        m.cycle_count,
                        m.temperature_c,
                        m.voltage_window_lower_v,
                        m.voltage_window_upper_v,
                        m.source_page,
                        m.section_type,
                        m.table_or_figure_ref,
                        m.evidence_quote,
                        m.extraction_method,
                        m.validation_status,
                    ),
                )

            # Evidence Records
            for ev in sample.evidence_records:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO entity_evidence (
                        evidence_id, paper_id, page_number, section_type, text_snippet, table_or_figure_ref
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ev.evidence_id,
                        ev.paper_id,
                        ev.page_number,
                        ev.section_type,
                        ev.text_snippet,
                        ev.table_or_figure_ref,
                    ),
                )

        conn.commit()


def list_material_samples(
    paper_id: Optional[str] = None,
    dopant: Optional[str] = None,
    min_crate: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """List resolved material samples with structured condition summaries."""
    init_entity_tables()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT s.sample_id, s.paper_id, s.sample_label, s.provenance_type,
                   s.resolution_status, s.resolution_confidence, s.resolution_notes,
                   s.is_unresolved,
                   c.raw_formula, c.base_lmfp_formula, c.mn_ratio, c.fe_ratio,
                   c.dopants_json, c.modifications_json,
                   syn.method AS synthesis_method, syn.calcination_temp_c, syn.atmosphere,
                   syn.precursor_salts_json,
                   ch.crystal_structure, ch.space_group, ch.xrd_phase_purity, ch.morphology,
                   sec.citation_key AS secondary_citation_key, sec.primary_doi AS secondary_primary_doi
            FROM entity_samples s
            JOIN entity_compositions c ON s.composition_id = c.composition_id
            LEFT JOIN entity_synthesis_profiles syn ON s.synthesis_profile_id = syn.synthesis_profile_id
            LEFT JOIN entity_characterization_profiles ch ON s.characterization_profile_id = ch.characterization_profile_id
            LEFT JOIN secondary_citations sec ON s.secondary_citation_id = sec.citation_id
            WHERE 1=1
        """
        params: List[Any] = []
        if paper_id:
            query += " AND s.paper_id = ?"
            params.append(paper_id)

        rows = cursor.execute(query, params).fetchall()
        samples = []

        for r in rows:
            s_dict = dict(r)
            s_dict["dopants"] = json.loads(s_dict.pop("dopants_json") or "[]")
            s_dict["modifications"] = json.loads(s_dict.pop("modifications_json") or "[]")
            s_dict["precursor_salts"] = json.loads(s_dict.pop("precursor_salts_json") or "[]")
            s_dict["is_unresolved"] = bool(s_dict.get("is_unresolved", False))

            # Check dopant filter
            if dopant and not any(
                (d.get("symbol") or d.get("element", "")).lower() == dopant.lower()
                for d in s_dict["dopants"]
            ):
                continue

            # Fetch linked measurements
            m_rows = cursor.execute(
                """
                SELECT measurement_id, measurement_type, reported_value, normalized_value,
                       normalized_unit, c_rate, cycle_count, temperature_c,
                       voltage_window_lower_v, voltage_window_upper_v, source_page,
                       table_or_figure_ref, evidence_quote, validation_status
                FROM entity_measurements
                WHERE sample_id = ?
                ORDER BY c_rate ASC, cycle_count ASC
                """,
                (s_dict["sample_id"],),
            ).fetchall()

            meas_list = [dict(m) for m in m_rows]
            if min_crate is not None:
                meas_list = [m for m in meas_list if m.get("c_rate") is not None and m.get("c_rate") >= min_crate]

            s_dict["measurements"] = meas_list
            samples.append(s_dict)

        return samples


def get_material_sample_graph(sample_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full entity graph for a single MaterialSample."""
    samples = list_material_samples()
    for s in samples:
        if s["sample_id"] == sample_id:
            return s
    return None


def update_material_sample(
    sample_id: str,
    sample_label: Optional[str] = None,
    resolution_status: Optional[str] = None,
    resolution_notes: Optional[str] = None,
    is_unresolved: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update resolution metadata for a sample in entity_samples.
    Allows manual reviewer disambiguation without modifying master dataset or auto-approving reviews.
    """
    init_entity_tables()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        if sample_label is not None:
            updates.append("sample_label = ?")
            params.append(sample_label)
        if resolution_status is not None:
            updates.append("resolution_status = ?")
            params.append(resolution_status)
        if resolution_notes is not None:
            updates.append("resolution_notes = ?")
            params.append(resolution_notes)
        if is_unresolved is not None:
            updates.append("is_unresolved = ?")
            params.append(1 if is_unresolved else 0)

        if updates:
            params.append(sample_id)
            cursor.execute(
                f"UPDATE entity_samples SET {', '.join(updates)} WHERE sample_id = ?",
                params,
            )
            conn.commit()

    return get_material_sample_graph(sample_id)


def populate_entities_from_existing_reviews():
    """
    Bootstrap the Stage 4 entity graph from reviewed literature records in `extraction_reviews`.
    Preserves all existing reviews, quarantine flags, and export blocks.
    """
    from literature.review_store import list_reviews

    init_entity_tables()
    all_reviews = list_reviews()

    # 1. Process srep26686
    srep_reviews = [r for r in all_reviews if "srep26686" in r.get("source_pdf", "").lower()]
    if srep_reviews:
        paper_id = "srep26686"
        srep_paper = PaperEntity(
            paper_id=paper_id,
            title="Hierarchical 3D porous LiMn0.75Fe0.25PO4/rGO microspheres",
            doi="10.1038/srep26686",
            authors="Scientific Reports 6:26686",
            year=2016,
            journal="Scientific Reports",
            is_review_paper=False,
            source_pdf="srep26686.pdf",
        )

        # Build SD_NO3 sample
        comp_base = CompositionEntity(
            composition_id="comp_LiMn0_75Fe0_25PO4",
            raw_formula="LiMn0.75Fe0.25PO4",
            base_lmfp_formula="LiMn0.75Fe0.25PO4",
            mn_ratio=0.75,
            fe_ratio=0.25,
            li_stoichiometry=1.0,
            is_stoichiometric=True,
        )

        syn_sd_no3 = SynthesisProfileEntity(
            synthesis_profile_id=f"syn_{paper_id}_SD_NO3",
            method="Salt-assisted spray drying",
            calcination_temp_c=650.0,
            calcination_time_h=6.0,
            atmosphere="Ar/H2 (95/5 vol%)",
            precursor_salts=["Fe(NO3)3", "Mn(NO3)2", "LiNO3", "H3PO4"],
            raw_evidence="Synthesized from nitrate metal salts; TR-XRD confirmed residual Fe2O3 impurity.",
            source_page=5,
        )

        char_sd_no3 = CharacterizationProfileEntity(
            characterization_profile_id=f"char_{paper_id}_SD_NO3",
            crystal_structure="orthorhombic olivine",
            space_group="Pnma",
            xrd_phase_purity="trace Fe2O3 impurity",
            impurity_phases=["Fe2O3"],
            morphology="microspheres with unreacted iron oxide",
            source_page=5,
        )

        meas_sd_no3 = [
            PropertyMeasurementEntity(
                measurement_id=f"meas_{paper_id}_SD_NO3_005c",
                sample_id=f"{paper_id}_SD_NO3",
                paper_id=paper_id,
                measurement_type="discharge_capacity",
                reported_value="45 mAh/g",
                reported_unit="mAh/g",
                normalized_value=45.0,
                normalized_unit="mAh/g",
                c_rate=0.05,
                source_page=7,
                section_type="RESULTS",
                table_or_figure_ref="Figure 7(a)",
                evidence_quote="At 0.05 C, SD_NO3 delivered 45 mAh/g, whereas SD_SO4 delivered 114 mAh/g.",
            )
        ]

        sample_sd_no3 = MaterialSample(
            sample_id=f"{paper_id}_SD_NO3",
            paper_id=paper_id,
            sample_label="SD_NO3",
            composition=comp_base,
            synthesis_profile=syn_sd_no3,
            characterization_profile=char_sd_no3,
            provenance_type=ProvenanceType.PRIMARY_EXPERIMENTAL,
            resolution_status=ResolutionStatus.CONFIRMED_EXPLICIT,
            resolution_confidence=1.0,
            resolution_notes="Explicit sample designation for nitrate precursor in srep26686.",
            measurements=meas_sd_no3,
        )

        # Build SD_SO4 sample
        syn_sd_so4 = SynthesisProfileEntity(
            synthesis_profile_id=f"syn_{paper_id}_SD_SO4",
            method="Salt-assisted spray drying",
            calcination_temp_c=650.0,
            calcination_time_h=6.0,
            atmosphere="Ar/H2 (95/5 vol%)",
            precursor_salts=["FeSO4.7H2O", "MnSO4.H2O", "LiOH.H2O", "H3PO4"],
            raw_evidence="Synthesized from sulfate metal salts; in-situ TR-XRD confirmed phase-pure Pnma olivine.",
            source_page=5,
        )

        char_sd_so4 = CharacterizationProfileEntity(
            characterization_profile_id=f"char_{paper_id}_SD_SO4",
            crystal_structure="orthorhombic olivine",
            space_group="Pnma",
            xrd_phase_purity="phase-pure olivine",
            impurity_phases=[],
            morphology="3D porous microspheres",
            source_page=5,
        )

        meas_sd_so4 = [
            PropertyMeasurementEntity(
                measurement_id=f"meas_{paper_id}_SD_SO4_005c",
                sample_id=f"{paper_id}_SD_SO4",
                paper_id=paper_id,
                measurement_type="discharge_capacity",
                reported_value="114 mAh/g",
                reported_unit="mAh/g",
                normalized_value=114.0,
                normalized_unit="mAh/g",
                c_rate=0.05,
                source_page=7,
                section_type="RESULTS",
                table_or_figure_ref="Figure 7(a)",
                evidence_quote="At 0.05 C, SD_NO3 delivered 45 mAh/g, whereas SD_SO4 delivered 114 mAh/g.",
            )
        ]

        sample_sd_so4 = MaterialSample(
            sample_id=f"{paper_id}_SD_SO4",
            paper_id=paper_id,
            sample_label="SD_SO4",
            composition=comp_base,
            synthesis_profile=syn_sd_so4,
            characterization_profile=char_sd_so4,
            provenance_type=ProvenanceType.PRIMARY_EXPERIMENTAL,
            resolution_status=ResolutionStatus.CONFIRMED_EXPLICIT,
            resolution_confidence=1.0,
            resolution_notes="Explicit sample designation for sulfate precursor in srep26686.",
            measurements=meas_sd_so4,
        )

        # Build LiMn0.75Fe0.25PO4/rGO composite sample
        comp_rgo = CompositionEntity(
            composition_id="comp_LiMn0_75Fe0_25PO4_rGO",
            raw_formula="LiMn0.75Fe0.25PO4/rGO",
            base_lmfp_formula="LiMn0.75Fe0.25PO4",
            mn_ratio=0.75,
            fe_ratio=0.25,
            li_stoichiometry=1.0,
            composite_modifications=[
                CompositeModificationEntity(
                    modification_id="mod_rgo_srep",
                    modification_type="rgo",
                    carbon_source="reduced graphene oxide",
                    morphology="3D interconnected conductive wrapping",
                )
            ],
        )

        char_rgo = CharacterizationProfileEntity(
            characterization_profile_id=f"char_{paper_id}_rGO",
            crystal_structure="orthorhombic olivine",
            space_group="Pnma",
            xrd_phase_purity="phase-pure olivine",
            morphology="hierarchical 3D porous microspheres wrapped by rGO",
            source_page=2,
        )

        meas_rgo = [
            PropertyMeasurementEntity(
                measurement_id=f"meas_{paper_id}_rgo_ret_10c",
                sample_id=f"{paper_id}_LiMn0_75Fe0_25PO4_rGO",
                paper_id=paper_id,
                measurement_type="capacity_retention",
                reported_value="93.0%",
                reported_unit="%",
                normalized_value=93.0,
                normalized_unit="%",
                c_rate=10.0,
                cycle_count=1000,
                source_page=1,
                section_type="ABSTRACT",
                evidence_quote="93% capacity retention after 1,000 cycles at 10 C.",
            ),
            PropertyMeasurementEntity(
                measurement_id=f"meas_{paper_id}_rgo_ret_20c",
                sample_id=f"{paper_id}_LiMn0_75Fe0_25PO4_rGO",
                paper_id=paper_id,
                measurement_type="capacity_retention",
                reported_value="76.0%",
                reported_unit="%",
                normalized_value=76.0,
                normalized_unit="%",
                c_rate=20.0,
                cycle_count=1000,
                source_page=1,
                section_type="ABSTRACT",
                evidence_quote="76% capacity retention after 1,000 cycles at 20 C.",
            ),
        ]

        sample_rgo = MaterialSample(
            sample_id=f"{paper_id}_LiMn0_75Fe0_25PO4_rGO",
            paper_id=paper_id,
            sample_label="LiMn0.75Fe0.25PO4/rGO",
            composition=comp_rgo,
            synthesis_profile=syn_sd_so4,
            characterization_profile=char_rgo,
            provenance_type=ProvenanceType.PRIMARY_EXPERIMENTAL,
            resolution_status=ResolutionStatus.CONFIRMED_MODIFICATION,
            resolution_confidence=0.95,
            resolution_notes="Composite modification with 3D rGO wrapping.",
            measurements=meas_rgo,
        )

        srep_paper.samples = [sample_sd_no3, sample_sd_so4, sample_rgo]
        save_paper_entity_graph(srep_paper)

    # 2. Process Review Paper (Lithium manganese iron phosphate materials... Reviews 1-7)
    rev_paper_reviews = [
        r for r in all_reviews
        if "lithium manganese iron phosphate materials" in r.get("source_pdf", "").lower()
    ]
    if rev_paper_reviews:
        rev_paper_id = "Lithium_manganese_iron_phosphate_materials__Design__progress__and_challenges"
        rev_paper = PaperEntity(
            paper_id=rev_paper_id,
            title="Lithium manganese iron phosphate materials: Design, progress, and challenges",
            authors="Review Authors",
            year=2023,
            is_review_paper=True,
            source_pdf="Lithium manganese iron phosphate materials_ Design, progress, and challenges.pdf",
        )

        # Secondary Citation [79]
        cit_79 = SecondaryCitationLink(
            citation_id=f"cit_79_{rev_paper_id}",
            review_paper_id=rev_paper_id,
            citation_key="[79]",
            primary_title="Original study cited as [79]",
            is_verified=False,
            notes="Secondary citation from review paper table on page 18.",
        )

        comp_79 = CompositionEntity(
            composition_id="comp_LiMn0_5Fe0_5PO4_NS",
            raw_formula="LiMn0.5Fe0.5PO4",
            base_lmfp_formula="LiMn0.5Fe0.5PO4",
            mn_ratio=0.5,
            fe_ratio=0.5,
            li_stoichiometry=1.0,
            dopants=[
                DopantEntity(dopant_id="dop_N_79", element="N", substitution_site="anion", precursor_agent="CTAB, TAA"),
                DopantEntity(dopant_id="dop_S_79", element="S", substitution_site="anion", precursor_agent="CTAB, TAA"),
            ],
        )

        syn_79 = SynthesisProfileEntity(
            synthesis_profile_id=f"syn_{rev_paper_id}_ref79",
            method="Solvothermal method",
            raw_evidence="Solvothermal method using CTAB and TAA surfactants.",
            source_page=18,
        )

        meas_79 = [
            PropertyMeasurementEntity(
                measurement_id=f"meas_{rev_paper_id}_ref79_01c",
                sample_id=f"{rev_paper_id}_Ref79_LiMn0_5Fe0_5PO4",
                paper_id=rev_paper_id,
                measurement_type="discharge_capacity",
                reported_value="166.8 mAh/g",
                reported_unit="mAh/g",
                normalized_value=166.8,
                normalized_unit="mAh/g",
                c_rate=0.1,
                voltage_window_lower_v=2.5,
                voltage_window_upper_v=4.5,
                source_page=18,
                table_or_figure_ref="Table (Page 18)",
                evidence_quote="166.8 (0.1 C), 118.9 (5 C) | 100.0% (100 cycles, 1 C), 92.0% (1000 cycles, 5 C) | [79]",
            ),
            PropertyMeasurementEntity(
                measurement_id=f"meas_{rev_paper_id}_ref79_5c",
                sample_id=f"{rev_paper_id}_Ref79_LiMn0_5Fe0_5PO4",
                paper_id=rev_paper_id,
                measurement_type="discharge_capacity",
                reported_value="118.9 mAh/g",
                reported_unit="mAh/g",
                normalized_value=118.9,
                normalized_unit="mAh/g",
                c_rate=5.0,
                voltage_window_lower_v=2.5,
                voltage_window_upper_v=4.5,
                source_page=18,
                table_or_figure_ref="Table (Page 18)",
                evidence_quote="166.8 (0.1 C), 118.9 (5 C) | 100.0% (100 cycles, 1 C), 92.0% (1000 cycles, 5 C) | [79]",
            ),
            PropertyMeasurementEntity(
                measurement_id=f"meas_{rev_paper_id}_ref79_ret_5c",
                sample_id=f"{rev_paper_id}_Ref79_LiMn0_5Fe0_5PO4",
                paper_id=rev_paper_id,
                measurement_type="capacity_retention",
                reported_value="92.0%",
                reported_unit="%",
                normalized_value=92.0,
                normalized_unit="%",
                c_rate=5.0,
                cycle_count=1000,
                voltage_window_lower_v=2.5,
                voltage_window_upper_v=4.5,
                source_page=18,
                table_or_figure_ref="Table (Page 18)",
                evidence_quote="92.0% (1000 cycles, 5 C)",
            ),
        ]

        sample_79 = MaterialSample(
            sample_id=f"{rev_paper_id}_Ref79_LiMn0_5Fe0_5PO4",
            paper_id=rev_paper_id,
            sample_label="Ref79_LiMn0.5Fe0.5PO4_NS",
            composition=comp_79,
            synthesis_profile=syn_79,
            provenance_type=ProvenanceType.SECONDARY_REVIEW,
            resolution_status=ResolutionStatus.SECONDARY_CITATION,
            resolution_confidence=0.85,
            resolution_notes="Secondary citation from review paper table citing reference [79].",
            secondary_citation=cit_79,
            measurements=meas_79,
        )

        # Secondary Citation [29] (Review #7)
        cit_29 = SecondaryCitationLink(
            citation_id=f"cit_29_{rev_paper_id}",
            review_paper_id=rev_paper_id,
            citation_key="[29]",
            primary_title="Original Ni-doped study cited as [29]",
            is_verified=False,
            notes="Secondary citation from review paper table on page 18. Export blocked pending primary DOI verification.",
        )

        comp_29 = CompositionEntity(
            composition_id="comp_LiMn0_8Fe0_2PO4_Ni",
            raw_formula="LiMn0.8Fe0.2PO4",
            base_lmfp_formula="LiMn0.8Fe0.2PO4",
            mn_ratio=0.8,
            fe_ratio=0.2,
            li_stoichiometry=1.0,
            dopants=[
                DopantEntity(dopant_id="dop_Ni_29", element="Ni", molar_ratio=None, substitution_site="M2", precursor_agent="NiSO4.6H2O"),
            ],
        )

        syn_29 = SynthesisProfileEntity(
            synthesis_profile_id=f"syn_{rev_paper_id}_ref29",
            method="Solvothermal method",
            raw_evidence="Solvothermal method using NiSO4.6H2O precursor.",
            source_page=18,
        )

        meas_29 = [
            PropertyMeasurementEntity(
                measurement_id=f"meas_{rev_paper_id}_ref29_01c",
                sample_id=f"{rev_paper_id}_Ref29_LiMn0_8Fe0_2PO4_Ni",
                paper_id=rev_paper_id,
                measurement_type="discharge_capacity",
                reported_value="144.0 mAh/g",
                reported_unit="mAh/g",
                normalized_value=144.0,
                normalized_unit="mAh/g",
                c_rate=0.1,
                voltage_window_lower_v=2.5,
                voltage_window_upper_v=4.5,
                source_page=18,
                table_or_figure_ref="Table (Page 18)",
                evidence_quote="144.0 (0.1 C), 119.5 (2 C), 105.5 (10 C) | 2.0 mg/cm2 | 2.5-4.5 V | [29]",
            ),
            PropertyMeasurementEntity(
                measurement_id=f"meas_{rev_paper_id}_ref29_10c",
                sample_id=f"{rev_paper_id}_Ref29_LiMn0_8Fe0_2PO4_Ni",
                paper_id=rev_paper_id,
                measurement_type="discharge_capacity",
                reported_value="105.5 mAh/g",
                reported_unit="mAh/g",
                normalized_value=105.5,
                normalized_unit="mAh/g",
                c_rate=10.0,
                voltage_window_lower_v=2.5,
                voltage_window_upper_v=4.5,
                source_page=18,
                table_or_figure_ref="Table (Page 18)",
                evidence_quote="105.5 (10 C) | 88.68% (500 cycles, 10 C)",
            ),
            PropertyMeasurementEntity(
                measurement_id=f"meas_{rev_paper_id}_ref29_ret_10c",
                sample_id=f"{rev_paper_id}_Ref29_LiMn0_8Fe0_2PO4_Ni",
                paper_id=rev_paper_id,
                measurement_type="capacity_retention",
                reported_value="88.68%",
                reported_unit="%",
                normalized_value=88.68,
                normalized_unit="%",
                c_rate=10.0,
                cycle_count=500,
                voltage_window_lower_v=2.5,
                voltage_window_upper_v=4.5,
                source_page=18,
                table_or_figure_ref="Table (Page 18)",
                evidence_quote="88.68% (500 cycles, 10 C)",
            ),
        ]

        sample_29 = MaterialSample(
            sample_id=f"{rev_paper_id}_Ref29_LiMn0_8Fe0_2PO4_Ni",
            paper_id=rev_paper_id,
            sample_label="Ref29_LiMn0.8Fe0.2PO4_Ni",
            composition=comp_29,
            synthesis_profile=syn_29,
            provenance_type=ProvenanceType.SECONDARY_REVIEW,
            resolution_status=ResolutionStatus.SECONDARY_CITATION,
            resolution_confidence=0.85,
            resolution_notes="Secondary citation from review paper table citing reference [29]. Preserved as approved review record #7 but export-blocked.",
            secondary_citation=cit_29,
            measurements=meas_29,
        )

        rev_paper.secondary_citations = [cit_79, cit_29]
        rev_paper.samples = [sample_79, sample_29]
        save_paper_entity_graph(rev_paper)


def populate_samples_from_master_dataset(limit: Optional[int] = None):
    """
    Map master literature dataset rows from `data/literature_reference.csv`
    into the Stage 4 sample-centric entity graph schema.
    """
    import pandas as pd
    from literature.dataset_export import CSV_PATH, NUMERIC_COLUMNS

    if not CSV_PATH.exists():
        return

    init_entity_tables()
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    if limit:
        df = df.head(limit)

    papers_map: Dict[str, PaperEntity] = {}

    for _, row in df.iterrows():
        p_id = str(row.get("Paper_ID") or "Unknown_Paper").strip()
        s_id = str(row.get("Sample_ID") or f"Sample_{uuid.uuid4().hex[:6]}").strip()
        title = str(row.get("Paper_Title") or p_id)
        doi = str(row.get("DOI")) if pd.notna(row.get("DOI")) else None
        year = int(row.get("Year")) if pd.notna(row.get("Year")) else None

        if p_id not in papers_map:
            papers_map[p_id] = PaperEntity(
                paper_id=p_id,
                title=title,
                doi=doi,
                year=year,
                is_review_paper=False,
            )

        # Composition
        raw_comp = str(row.get("Composition_Formula") or "LiMn0.5Fe0.5PO4").strip()
        base_comp = str(row.get("Base_LMFP_Composition") or raw_comp).strip()
        mn_r = float(row.get("Mn_Ratio")) if pd.notna(row.get("Mn_Ratio")) else 0.5
        fe_r = float(row.get("Fe_Ratio")) if pd.notna(row.get("Fe_Ratio")) else 0.5

        dop_elem = str(row.get("Dopant_Element") or "")
        dop_ratio = float(row.get("Dopant_Molar_Ratio")) if pd.notna(row.get("Dopant_Molar_Ratio")) else None

        dopants = []
        if dop_elem and dop_elem not in {"None/Undoped", "Unspecified", "nan"}:
            for elem in dop_elem.split(";"):
                elem_clean = elem.strip()
                if elem_clean:
                    dopants.append(
                        DopantEntity(
                            dopant_id=f"dop_{p_id}_{s_id}_{elem_clean}",
                            element=elem_clean,
                            molar_ratio=dop_ratio,
                            substitution_site="M2",
                        )
                    )

        comp_ent = CompositionEntity(
            composition_id=f"comp_{p_id}_{s_id}",
            raw_formula=raw_comp,
            base_lmfp_formula=base_comp,
            mn_ratio=mn_r,
            fe_ratio=fe_r,
            dopants=dopants,
        )

        # Synthesis
        synth_method = str(row.get("Synthesis_Method") or "Unspecified")
        calc_temp = float(row.get("Calcination_Temp_1_C")) if pd.notna(row.get("Calcination_Temp_1_C")) else None
        calc_time = float(row.get("Calcination_Time_1_h")) if pd.notna(row.get("Calcination_Time_1_h")) else None

        syn_ent = SynthesisProfileEntity(
            synthesis_profile_id=f"syn_{p_id}_{s_id}",
            method=synth_method,
            calcination_temp_c=calc_temp,
            calcination_time_h=calc_time,
        )

        # Characterization
        xrd_purity = str(row.get("XRD_Phase_Purity") or "")
        imp_phase = str(row.get("Impurity_Phase_Identified") or "")
        impurities = [imp_phase] if imp_phase and imp_phase != "nan" else []

        char_ent = CharacterizationProfileEntity(
            characterization_profile_id=f"char_{p_id}_{s_id}",
            crystal_structure="orthorhombic olivine",
            space_group="Pnma",
            xrd_phase_purity=xrd_purity if xrd_purity != "nan" else None,
            impurity_phases=impurities,
        )

        # Measurements
        measurements = []
        for rate, col in [
            (0.05, "Discharge_Capacity_0_05C_mAh_g"),
            (0.1, "Discharge_Capacity_0_1C_mAh_g"),
            (1.0, "Discharge_Capacity_1C_mAh_g"),
            (2.0, "Discharge_Capacity_2C_mAh_g"),
            (5.0, "Discharge_Capacity_5C_mAh_g"),
        ]:
            val = row.get(col)
            if pd.notna(val):
                try:
                    num_val = float(str(val).replace("mAh/g", "").strip())
                    measurements.append(
                        PropertyMeasurementEntity(
                            measurement_id=f"meas_{p_id}_{s_id}_{col}",
                            sample_id=s_id,
                            paper_id=p_id,
                            measurement_type="discharge_capacity",
                            reported_value=f"{num_val} mAh/g",
                            reported_unit="mAh/g",
                            normalized_value=num_val,
                            normalized_unit="mAh/g",
                            c_rate=rate,
                            extraction_method="master_dataset_import",
                        )
                    )
                except ValueError:
                    pass

        # Retention
        ret_val = row.get("Capacity_Retention_percent")
        cycles = row.get("Cycle_Life_cycles")
        if pd.notna(ret_val):
            try:
                num_ret = float(str(ret_val).replace("%", "").strip())
                num_cycles = int(float(str(cycles).strip())) if pd.notna(cycles) else None
                measurements.append(
                    PropertyMeasurementEntity(
                        measurement_id=f"meas_{p_id}_{s_id}_retention",
                        sample_id=s_id,
                        paper_id=p_id,
                        measurement_type="capacity_retention",
                        reported_value=f"{num_ret}%",
                        reported_unit="%",
                        normalized_value=num_ret,
                        normalized_unit="%",
                        cycle_count=num_cycles,
                        extraction_method="master_dataset_import",
                    )
                )
            except ValueError:
                pass

        sample = MaterialSample(
            sample_id=s_id,
            paper_id=p_id,
            sample_label=s_id,
            composition=comp_ent,
            synthesis_profile=syn_ent,
            characterization_profile=char_ent,
            provenance_type=ProvenanceType.PRIMARY_EXPERIMENTAL,
            resolution_status=ResolutionStatus.CONFIRMED_EXPLICIT,
            resolution_confidence=1.0,
            resolution_notes=f"Imported from master literature dataset sample {s_id}.",
            measurements=measurements,
        )
        papers_map[p_id].samples.append(sample)

    for paper in papers_map.values():
        save_paper_entity_graph(paper)


