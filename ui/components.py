"""
Streamlit UI Components for HE-LMFP Materials Designer.
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Any, Tuple, Optional

from chemistry.dopants import (
    ALLOWED_DOPANTS,
    EXCLUDED_DOPANTS,
    MIN_DOPANTS,
    MAX_DOPANTS,
    MIN_DOPANT_CONC,
    MAX_DOPANT_CONC,
    DOPANT_DATABASE,
    get_valid_oxidation_states
)
from chemistry.formula import ChemicalFormula
from chemistry.charge_balance import ChargeBalanceResult
from chemistry.entropy import EntropyResult
from chemistry.capacity import CapacityMetrics
from chemistry.validation import ValidationReport
from design.modifications import MaterialModifications
from design.processing import SynthesisProcessing, NOT_SPECIFIED
from design.characterization import CharacterizationPlan
from design.electrochemistry import ElectrochemicalPlan
from literature.matcher import MatchResult, MatchStatus
from literature.evidence import format_evidence_report
from models.ml.predictor import predict_composition_performance
from experiments.models import (
    LabExperiment,
    ExperimentStatus,
    ActualSynthesisData,
    ActualCharacterizationData,
    ActualElectrochemicalData
)
from experiments.storage import (
    save_experiment,
    list_experiments,
    delete_experiment,
    load_experiment,
    export_experiments_to_csv,
    export_experiments_to_json,
    get_database_mode_info
)
from experiments.validation import validate_lab_experiment
from experiments.comparison import generate_comparison_matrix, ComparisonMatrix


def render_header():
    """Render project header and title badge."""
    st.markdown("""
    <div style="background-color:#0e1117; padding:20px; border-radius:10px; border:1fr solid #1e2638; margin-bottom:20px;">
        <h1 style="color:#00d2ff; text-align:center; margin-bottom:5px;">High-Entropy Doped LMFP Formula & Materials Design Platform</h1>
        <p style="color:#a0aab8; text-align:center; font-size:16px;">
            AI-Assisted Computational Materials Design Engine for Lithium Manganese Iron Phosphate Cathodes
        </p>
        <div style="text-align:center; font-size:12px; color:#6b7280; margin-top:5px;">
            <span>Deterministic Scientific Chemistry Engine • Version 1.0</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_host_composition_section(mn_default: float = 0.65, fe_default: float = 0.26) -> Tuple[float, float]:
    """Render Mn and Fe host composition inputs."""
    st.subheader("1. Primary Host Composition (M2 Site)")
    st.caption("Mn and Fe are fixed in +2 oxidation state (Mn²⁺ / Fe²⁺).")
    
    col1, col2 = st.columns(2)
    with col1:
        mn_frac = st.slider(
            "Mn Fraction (Allowed: 0.60 – 0.75)",
            min_value=0.50,
            max_value=0.85,
            value=mn_default,
            step=0.01,
            format="%.2f",
            help="Primary transition metal cation Mn²⁺ on M2 site."
        )
        st.info(f"Selected Mn²⁺: **{mn_frac:.2f}** mol (Allowed: 0.60–0.75)")
        
    with col2:
        fe_frac = st.slider(
            "Fe Fraction (Allowed: 0.10 – 0.30)",
            min_value=0.05,
            max_value=0.40,
            value=fe_default,
            step=0.01,
            format="%.2f",
            help="Primary transition metal cation Fe²⁺ on M2 site."
        )
        st.info(f"Selected Fe²⁺: **{fe_frac:.2f}** mol (Allowed: 0.10–0.30)")

    return mn_frac, fe_frac

def render_dopant_selection_section(default_dopants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Render multi-element dopant selection table with concentration and oxidation state inputs."""
    st.subheader("2. Multi-Element Dopant Selection (3–5 Dopants)")
    st.caption("Select 3 to 5 dopant elements in addition to Mn and Fe. Excluded elements: Cr (excluded), Co (excluded due to cost).")
    
    num_dopants = st.radio(
        "Number of Dopant Elements:",
        options=[3, 4, 5],
        index=len(default_dopants) - 3 if 3 <= len(default_dopants) <= 5 else 2,
        horizontal=True
    )
    
    # Excluded status notice
    st.warning("⚠️ Strictly Excluded Elements: **Cr** (excluded) | **Co** (excluded due to raw material cost)")
    
    selected_dopants_data = []
    cols = st.columns(num_dopants)
    
    for i in range(num_dopants):
        with cols[i]:
            st.markdown(f"**Dopant #{i+1}**")
            
            default_sym = default_dopants[i]["symbol"] if i < len(default_dopants) else ALLOWED_DOPANTS[i % len(ALLOWED_DOPANTS)]
            if default_sym not in ALLOWED_DOPANTS:
                default_sym = ALLOWED_DOPANTS[0]
                
            idx = ALLOWED_DOPANTS.index(default_sym) if default_sym in ALLOWED_DOPANTS else 0
            
            sym = st.selectbox(
                f"Element #{i+1}",
                options=ALLOWED_DOPANTS,
                index=idx,
                key=f"dopant_elem_{i}"
            )
            
            default_conc = default_dopants[i]["fraction"] if i < len(default_dopants) else 0.02
            conc = st.number_input(
                f"Conc (mol)",
                min_value=0.001,
                max_value=0.100,
                value=float(default_conc),
                step=0.005,
                format="%.3f",
                key=f"dopant_conc_{i}",
                help="Default allowed range: 0.005 - 0.05 mol"
            )
            
            valid_ox_states = get_valid_oxidation_states(sym)
            default_ox = default_dopants[i]["oxidation_state"] if i < len(default_dopants) and default_dopants[i]["oxidation_state"] in valid_ox_states else valid_ox_states[0]
            
            if len(valid_ox_states) > 1:
                ox = st.selectbox(
                    f"Oxidation State",
                    options=valid_ox_states,
                    index=valid_ox_states.index(default_ox),
                    format_func=lambda x: f"+{x}",
                    key=f"dopant_ox_{i}"
                )
            else:
                ox = valid_ox_states[0]
                st.write(f"Oxidation State: **+{ox}** (Fixed)")
                
            selected_dopants_data.append({
                "symbol": sym,
                "fraction": conc,
                "oxidation_state": ox
            })
            
    return selected_dopants_data

def render_charge_balance_section(cb_result: ChargeBalanceResult):
    """Render charge balance details and strategy."""
    st.subheader("3. Charge Balance & Site Occupancy Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total M2 Occupancy", f"{cb_result.m2_occupancy:.4f}", delta="Ideal: 1.0000")
    with col2:
        st.metric("Total M2 Cation Charge (Q_M2)", f"{cb_result.q_m2:.4f} e")
    with col3:
        st.metric("Required Li Stoichiometry", f"{cb_result.adjusted_li:.4f}")
    with col4:
        st.metric("Li Vacancy Fraction (δ)", f"{cb_result.delta_li:.4f}")
        
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Total Positive Charge", f"{cb_result.q_total_positive:+.4f} e")
    with col_b:
        st.metric("Total Negative Charge", f"{cb_result.q_total_negative:+.4f} e")
    with col_c:
        st.metric("Net Cell Charge", f"{cb_result.net_charge_after:+.4f} e")
    with col_d:
        if cb_result.is_balanced and cb_result.m2_occupancy_valid:
            st.success("STATUS: PASS (Neutral)")
        else:
            st.error("STATUS: INVALID (Imbalanced)")
        
    if not cb_result.m2_occupancy_valid:
        st.error(f"❌ **CRITICAL M2 OCCUPANCY VIOLATION**: Total M2 site occupancy sum ({cb_result.m2_occupancy:.4f}) does not equal **1.0000** (Tolerance ±0.0001). Formula generation, charge balancing, and theoretical capacity calculations are **BLOCKED** until M2 occupancy is adjusted to 1.0000.")
    elif cb_result.is_balanced:
        st.success("✅ **Charge Neutrality Satisfied**: Formula is mathematically charge-balanced.")
    else:
        st.error(f"❌ **Charge Imbalance Detected**: Net charge = {cb_result.net_charge_after:+.4f} e")
        
    if cb_result.adjustment_details:
        st.info("ℹ️ **Transparent Adjustment Log** (No Silent Editing):\n" + "\n".join([f"- {d['reason']}" for d in cb_result.adjustment_details]))

def render_formula_card(formula: Optional[ChemicalFormula], cb_result: ChargeBalanceResult):
    """Display prominent chemical formula card and structured breakdown table."""
    st.subheader("4. Generated Chemical Formula")
    
    if formula is None or not cb_result.m2_occupancy_valid:
        st.markdown(f"""
        <div style="background-color:#451a1a; padding:15px; border-radius:8px; border-left:6px solid #ef4444; text-align:center;">
            <span style="font-size:14px; color:#fca5a5;">FORMULA GENERATION BLOCKED</span><br/>
            <span style="font-size:20px; font-weight:bold; color:#f8fafc; font-family:monospace;">M2 Occupancy Violation ({cb_result.m2_occupancy:.4f} ≠ 1.0000)</span>
        </div>
        """, unsafe_allow_html=True)
        st.error(f"❌ Cannot generate a chemical formula when total M2 site occupancy is {cb_result.m2_occupancy:.4f}. Please adjust Mn, Fe, or dopant fractions so that their sum equals 1.0000.")
        return

    st.markdown(f"""
    <div style="background-color:#1e293b; padding:15px; border-radius:8px; border-left:6px solid #3b82f6; text-align:center;">
        <span style="font-size:14px; color:#94a3b8;">GENERATED CHEMICAL FORMULA</span><br/>
        <span style="font-size:24px; font-weight:bold; color:#f8fafc; font-family:monospace;">{formula.formula_string}</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"Calculated Formula Molecular Mass: **{formula.molar_mass:.4f} g/mol**")
    
    # Table of components
    table_data = []
    for c in formula.components:
        table_data.append({
            "Element": c.element,
            "Cation/Anion Site": c.site,
            "Mole Fraction": f"{c.fraction:.4f}",
            "Oxidation State": f"+{c.oxidation_state}" if c.oxidation_state > 0 else f"{c.oxidation_state}",
            "Charge Contribution (e)": f"{c.charge_contribution:+.4f}",
            "Atomic Weight (g/mol)": f"{c.atomic_weight:.4f}"
        })
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

def render_entropy_section(entropy_res: Optional[EntropyResult]):
    """Render configurational entropy analysis panel."""
    st.subheader("5. Configurational Entropy Analysis (S_config)")
    
    if entropy_res is None:
        st.warning("⚠️ **Configurational Entropy Calculation Skipped**: Requires valid M2 occupancy = 1.0000.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("S_config (J mol⁻¹ K⁻¹)", f"{entropy_res.s_config_j_mol_k:.4f}")
    with col2:
        st.metric("S_config / R Ratio", f"{entropy_res.s_config_over_r:.4f}")
    with col3:
        st.metric("M2 Species Count", f"{entropy_res.num_m2_species}")
        
    st.warning(f"🏷️ **Entropy Classification**: {entropy_res.classification_label}")
    st.caption("Note: The ≥1.5R high-entropy threshold is a provisional reference classification requiring experimental verification.")

def render_literature_section(match_res: Optional[MatchResult]):
    """Render literature reference verification audit panel."""
    st.subheader("6. Literature & Prior Study Verification Audit")
    
    if match_res is None:
        st.error("❌ **Literature Verification Audit Blocked**: Chemical formula generation was blocked due to M2 site occupancy violation.")
        return

    if match_res.status == MatchStatus.LITERATURE_MATCH:
        st.success("✅ **LITERATURE MATCH FOUND**: This exact chemical composition has been reported in published scientific literature.")
    elif match_res.status == MatchStatus.NEAR_LITERATURE_MATCH:
        st.warning("⚠️ **NEAR LITERATURE MATCH**: Similar compositions exist in literature within stoichiometric tolerance.")
    elif match_res.status == MatchStatus.SUPERVISOR_REFERENCE:
        st.info("📌 **SUPERVISOR REFERENCE BASELINE**: Matches project reference baseline composition.")
    else:
        st.info("ℹ️ **NO MATCH IN CURRENT DATABASE**: No sufficiently matching record was found in the uploaded literature reference database.")
        
    ev_report = format_evidence_report(match_res)
    st.markdown(ev_report)

def render_capacity_section(cap_metrics: Optional[CapacityMetrics]):
    """Render theoretical and practical capacity reference panel."""
    st.subheader("7. Capacity & Electrochemical Reference")

    if cap_metrics is None:
        st.error("❌ **Capacity Metrics Blocked**: Cannot compute theoretical capacity metric without a valid generated chemical formula.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Project Reference Theoretical Capacity", f"{cap_metrics.reference_theoretical_capacity:.1f} mAh/g")
    with col2:
        st.metric("Formula-Based Calculated Capacity Metric", f"{cap_metrics.formula_calculated_capacity_metric:.1f} mAh/g")
    with col3:
        st.metric("Practical Target Range (0.1C)", f"{cap_metrics.practical_target_min:.0f}–{cap_metrics.practical_target_max:.0f} mAh/g")
        
    st.info(f"⚡ **Voltage Operating Window**: {cap_metrics.voltage_window_min:.1f} V – {cap_metrics.voltage_window_max:.1f} V")
    
    # C-rate Panel
    st.markdown("**C-Rate Testing Reference Panel**")
    c_df = pd.DataFrame(cap_metrics.c_rate_panel)
    c_df.columns = ["C-Rate", "Approximate Discharge Duration", "Operational Context"]
    st.table(c_df)
    st.caption(cap_metrics.disclaimer)

def render_modifications_section() -> MaterialModifications:
    """Render conductive modification choices (Carbon coating, CNT, mGO)."""
    st.subheader("7. Conductive Material Modifications (Carbon / CNT / mGO)")
    
    mode = st.radio(
        "Conductive Additive Option:",
        options=[
            "No conductive modification",
            "Carbon Coating Only",
            "CNT Only",
            "Carbon Coating + CNT"
        ],
        index=1,
        key="mod_mode_radio"
    )
    
    carbon_wt = 2.5
    cnt_wt = 1.0
    
    col1, col2 = st.columns(2)
    with col1:
        if mode in ["Carbon Coating Only", "Carbon Coating + CNT"]:
            carbon_wt = st.slider(
                "Carbon Coating wt% (Allowed max: 2.0 – 3.0 wt%)",
                min_value=0.5,
                max_value=5.0,
                value=2.5,
                step=0.1,
                format="%.1f",
                key="mod_carbon_slider"
            )
        else:
            st.write("Carbon Coating: Disabled")
            
    with col2:
        if mode in ["CNT Only", "Carbon Coating + CNT"]:
            cnt_wt = st.slider(
                "CNT wt% (Allowed max: 0.5 – 1.5 wt%)",
                min_value=0.1,
                max_value=3.0,
                value=1.0,
                step=0.1,
                format="%.1f",
                key="mod_cnt_slider"
            )
        else:
            st.write("CNT Addition: Disabled")
            
    # Future mGO Status
    st.info("📌 **mGO (Modified Graphene Oxide)** Status: *Future Option / Not part of current active V1 optimization* (Can be enabled in future optimization phases).")
    enable_mgo = st.checkbox("Enable mGO (Flagged as Future Feature)", value=False, key="mod_mgo_checkbox")
    
    from design.modifications import get_material_modifications
    return get_material_modifications(mode, carbon_wt, cnt_wt, enable_mgo)

def render_synthesis_section() -> SynthesisProcessing:
    """Render synthesis processing setup with configurable placeholders for unverified values."""
    st.subheader("8. Synthesis & Co-Precipitation Processing Setup")
    
    st.success("🔬 **Primary Required Synthesis Route**: **Co-precipitation**")
    st.caption("Sol-gel is excluded from active primary optimization workflow.")
    
    st.markdown("##### Synthesis & Calcination Parameters")
    st.caption("⚠️ Per supervisor directive: Unsupported synthesis parameters are NOT populated with invented default values. Configure placeholders below or keep as unverified.")
    
    col1, col2 = st.columns(2)
    with col1:
        precursors = st.text_input("Transition Metal Precursors", value=NOT_SPECIFIED)
        precipitating_agent = st.text_input("Precipitating Agent", value=NOT_SPECIFIED)
        chelating_agent = st.text_input("Chelating Agent / Complexing Agent", value=NOT_SPECIFIED)
        reaction_ph = st.text_input("Reaction pH", value=NOT_SPECIFIED)
        
    with col2:
        reaction_temp = st.text_input("Reaction Temperature (°C)", value=NOT_SPECIFIED)
        calc_temp = st.text_input("Calcination Temperature (°C)", value=NOT_SPECIFIED)
        calc_duration = st.text_input("Calcination Duration (h)", value=NOT_SPECIFIED)
        calc_atmos = st.text_input("Calcination Atmosphere", value=NOT_SPECIFIED)
        
    from design.processing import get_coprecipitation_processing
    return get_coprecipitation_processing(
        metal_precursors=precursors,
        precipitating_agent=precipitating_agent,
        chelating_agent=chelating_agent,
        reaction_ph=reaction_ph,
        reaction_temperature=reaction_temp,
        calcination_temperature=calc_temp,
        calcination_duration=calc_duration,
        calcination_atmosphere=calc_atmos
    )

def render_characterization_section() -> Tuple[CharacterizationPlan, ElectrochemicalPlan]:
    """Render physical and electrochemical characterization plans."""
    st.subheader("9. Material & Electrochemical Characterization Plan")
    
    tab1, tab2 = st.tabs(["Physical Characterization (5 Techniques)", "Electrochemical Characterization"])
    
    with tab1:
        from design.characterization import get_characterization_plan
        char_plan = get_characterization_plan()
        
        char_df = pd.DataFrame(char_plan.techniques)
        char_df.columns = ["Technique", "Full Technique Name", "Target Analysis & Purpose", "Protocol Status"]
        st.table(char_df)
        
    with tab2:
        from design.electrochemistry import get_electrochemical_plan
        elec_plan = get_electrochemical_plan()
        
        st.markdown(f"**Voltage Window**: `{elec_plan.voltage_min} V` to `{elec_plan.voltage_max} V`")
        for item in elec_plan.test_items:
            st.markdown(f"- **{item['test_name']}**: {item['description']}")
            
    return char_plan, elec_plan

def render_validation_section(val_report: ValidationReport):
    """Render validation status badge and log."""
    st.subheader("10. Chemical Validation & Safety Rule Audit")
    st.caption("Note: PASS/WARNING/INVALID status reflects system constraint validation checks (trial framework), not finalized scientific truth.")
    
    if val_report.overall_status == "PASS":
        st.success("✅ **VALIDATION STATUS: PASS** — All chemical rules and system constraints satisfied.")
    elif val_report.overall_status == "WARNING":
        st.warning("⚠️ **VALIDATION STATUS: WARNING** — Valid composition with cautionary or provisional notices.")
    else:
        st.error("❌ **VALIDATION STATUS: INVALID** — One or more hard chemical constraints violated.")
        
    if val_report.errors:
        st.markdown("##### ❌ Errors (Hard Constraint Violations)")
        for err in val_report.errors:
            st.error(f"• {err}")
            
    if val_report.warnings:
        st.markdown("##### ⚠️ Warnings & Provisional Alerts")
        for warn in val_report.warnings:
            st.warning(f"• {warn}")

def render_report_section(
    formula: Optional[ChemicalFormula],
    cb_result: ChargeBalanceResult,
    entropy_res: Optional[EntropyResult],
    cap_metrics: Optional[CapacityMetrics],
    mod_specs: MaterialModifications,
    synth_specs: SynthesisProcessing,
    val_report: ValidationReport,
    match_res: Optional[MatchResult] = None,
    experiment: Optional[LabExperiment] = None,
    comp_matrix: Optional[ComparisonMatrix] = None
):
    """Render final comprehensive material design summary report and export option."""
    st.subheader("12. Final Material Design Summary Report")
    
    if formula is None or not cb_result.m2_occupancy_valid:
        st.error("❌ **Design Report Incomplete**: Chemical formula generation is blocked because M2 site occupancy sum does not equal 1.0000.")
        st.markdown("### Hard Validation Errors Blocking Report Generation:")
        for err in val_report.errors:
            st.error(f"• {err}")
        return

    lit_status_str = match_res.status.value if match_res else "NOT_AUDITED"
    lit_summary = match_res.explanation if match_res else "Literature database check not executed."
    
    s_j_str = f"{entropy_res.s_config_j_mol_k:.4f}" if entropy_res else "N/A"
    s_r_str = f"{entropy_res.s_config_over_r:.4f}" if entropy_res else "N/A"
    entropy_class = entropy_res.classification_label if entropy_res else "N/A"
    
    ref_cap_str = f"{cap_metrics.reference_theoretical_capacity:.1f}" if cap_metrics else "N/A"
    calc_cap_str = f"{cap_metrics.formula_calculated_capacity_metric:.1f}" if cap_metrics else "N/A"
    target_cap_str = f"{cap_metrics.practical_target_min:.0f}–{cap_metrics.practical_target_max:.0f}" if cap_metrics else "N/A"
    v_win_str = f"{cap_metrics.voltage_window_min:.1f} – {cap_metrics.voltage_window_max:.1f}" if cap_metrics else "2.5 – 4.2"
    
    report_md = f"""# High-Entropy Doped LMFP Material Design Report

## 1. Chemical Formula & Stoichiometry
- **Generated Formula**: `{formula.formula_string}`
- **Formula Molar Mass**: `{formula.molar_mass:.4f} g/mol`
- **M2 Site Occupancy**: `{formula.m2_occupancy:.4f}` (Valid: {cb_result.m2_occupancy_valid})
- **Li Stoichiometry (1-δ)**: `{cb_result.adjusted_li:.4f}`
- **Li Vacancy Fraction (δ)**: `{cb_result.delta_li:.4f}`

## 2. Host Cations & Dopants
- **Mn Fraction**: `{formula.mn_fraction:.4f}` (Oxidation state: +2)
- **Fe Fraction**: `{formula.fe_fraction:.4f}` (Oxidation state: +2)
- **Dopants Selected**: {len(formula.dopants)} dopant elements
"""
    for d in formula.dopants:
        report_md += f"  - **{d.element}**: Fraction = `{d.fraction:.4f}`, Oxidation State = `+{d.oxidation_state}`\n"
        
    report_md += f"""
## 3. Charge Neutrality & Balance
- **M2 Site Cation Charge**: `{cb_result.q_m2:.4f} e`
- **Charge Balance Status**: {'Balanced' if cb_result.is_balanced else 'Imbalanced'}
- **Adjustment Strategy**: `{cb_result.adjustment_strategy}`

## 4. Entropy & Capacity Metrics
- **S_config**: `{s_j_str} J mol⁻¹ K⁻¹` (`{s_r_str} R`)
- **Entropy Classification**: `{entropy_class}`
- **Project Reference Theoretical Capacity**: `{ref_cap_str} mAh/g`
- **Formula-Based Calculated Capacity Metric**: `{calc_cap_str} mAh/g`
- **Practical Target Range**: `{target_cap_str} mAh/g at 0.1C`
- **Voltage Window**: `{v_win_str} V`

## 5. Literature & Prior Study Verification Audit
- **Literature Match Status**: `{lit_status_str}`
- **Matching Summary**: {lit_summary}

## 6. Conductive Additives & Modifications
- **Modification Mode**: `{mod_specs.modification_mode}`
- **Carbon Coating**: `{mod_specs.carbon_coating_wt_pct:.2f} wt%` (Enabled: {mod_specs.carbon_coating_enabled})
- **CNT Addition**: `{mod_specs.cnt_wt_pct:.2f} wt%` (Enabled: {mod_specs.cnt_enabled})
- **mGO Status**: `{mod_specs.mgo_status_label}`

## 7. Synthesis Processing Parameters (Co-precipitation)
- **Synthesis Route**: `{synth_specs.primary_synthesis_method}`
- **Transition Metal Precursors**: `{synth_specs.metal_precursors}`
- **Precipitating Agent**: `{synth_specs.precipitating_agent}`
- **Reaction pH**: `{synth_specs.reaction_ph}`
- **Calcination Temperature**: `{synth_specs.calcination_temperature}`
- **Calcination Atmosphere**: `{synth_specs.calcination_atmosphere}`

## 8. Electrochemical & Characterization Testing Protocols
- **Voltage Operating Window**: `{v_win_str} V`
- **Room-Temperature Cycling (25°C)**: Long-term capacity retention cycling at 25°C (1C/1C rate)
- **High-Temperature Cycling (55°C)**: Accelerated degradation cycling at 55°C to evaluate Mn dissolution and thermal stability
- **Low-Temperature Cycling (-20°C)**: Low-temperature capacity retention cycling and discharge performance at -20°C (0.1C rate)
"""

    if experiment:
        syn = experiment.synthesis_data
        char = experiment.characterization_data
        elec = experiment.electrochemical_data
        report_md += f"""
## 9. Laboratory Experiment Record
- **Experiment ID**: `{experiment.experiment_id}`
- **Sample ID**: `{experiment.sample_id}`
- **Operator**: `{experiment.operator}`
- **Batch ID**: `{experiment.batch_id}`
- **Experiment Status**: `{experiment.status.value}`
- **Notes**: {experiment.notes or 'None'}

### Actual Synthesis Results
- **Precursors**: `{syn.metal_precursors if syn else 'Unspecified'}`
- **Precursor Mass**: `{f'{syn.precursor_mass_g:.2f} g' if syn and syn.precursor_mass_g else 'Unspecified'}`
- **Reaction pH**: `{syn.reaction_ph if syn and syn.reaction_ph else 'Unspecified'}`
- **Calcination Temp**: `{f'{syn.calcination_temp_c:.1f} °C' if syn and syn.calcination_temp_c else 'Unspecified'}`
- **Yield**: `{f'{syn.yield_pct:.1f} %' if syn and syn.yield_pct else 'Unspecified'}`

### Actual Characterization Findings
- **XRD Phase Purity**: `{f'{char.xrd_phase_purity_pct:.1f} %' if char and char.xrd_phase_purity_pct else 'Unmeasured'}`
- **BET Surface Area**: `{f'{char.bet_surface_area_m2g:.2f} m²/g' if char and char.bet_surface_area_m2g else 'Unmeasured'}`
- **Electrical Conductivity**: `{char.electrical_conductivity_scm if char and char.electrical_conductivity_scm else 'Unmeasured'}`

### Actual Electrochemical Test Data
- **0.1C Discharge Capacity**: `{f'{elec.cap_0_1c:.1f} mAh/g' if elec and elec.cap_0_1c else 'Unmeasured'}`
- **1.0C Discharge Capacity**: `{f'{elec.cap_1c:.1f} mAh/g' if elec and elec.cap_1c else 'Unmeasured'}`
- **Initial Coulombic Efficiency (ICE)**: `{f'{elec.initial_coulombic_efficiency:.1f} %' if elec and elec.initial_coulombic_efficiency else 'Unmeasured'}`
- **Room-Temp (25°C) Retention**: `{f'{elec.retention_25c_pct:.1f} %' if elec and elec.retention_25c_pct else 'Unmeasured'}`
- **High-Temp (55°C) Retention**: `{f'{elec.retention_55c_pct:.1f} %' if elec and elec.retention_55c_pct else 'Unmeasured'}`
- **Low-Temp (-20°C) Retention**: `{f'{elec.retention_minus20c_pct:.1f} %' if elec and elec.retention_minus20c_pct else 'Unmeasured'}`
"""

    if comp_matrix:
        report_md += "\n## 10. Computational vs Experimental Comparison Summary\n"
        for r in comp_matrix.rows:
            c_val = f"{r.calculated_val} {r.unit}" if r.calculated_val is not None else "N/A"
            l_val = f"{r.literature_val} {r.unit}" if r.literature_val is not None else "N/A"
            e_val = f"{r.experimental_val} {r.unit}" if r.experimental_val is not None else "Not Measured"
            res_c = f"{r.residual_vs_calculated:+.1f} {r.unit}" if r.residual_vs_calculated is not None else "N/A"
            report_md += f"- **{r.property_name}**: Calculated = `{c_val}`, Literature = `{l_val}`, Experimental = `{e_val}` (Residual vs Calc: `{res_c}`)\n"

    report_md += f"""
## 11. Validation & Safety Audit
- **Overall Status**: `{val_report.overall_status}`
- **Errors Count**: `{len(val_report.errors)}`
- **Warnings Count**: `{len(val_report.warnings)}`
"""

    st.markdown(report_md)
    
    st.download_button(
        label="📥 Download Full Scientific Design Report (.md)",
        data=report_md,
        file_name=f"HE_LMFP_Design_Report_{formula.formula_string.replace('[','_').replace(']','_')}.md",
        mime="text/markdown"
    )


def render_lab_experiment_entry_section(
    formula: Optional[ChemicalFormula],
    mn_frac: float,
    fe_frac: float,
    dopants: List[Dict[str, Any]],
    mod_specs: MaterialModifications,
    current_exp: Optional[LabExperiment] = None
) -> Optional[LabExperiment]:
    """Render interactive laboratory experiment entry form for recording actual synthesis, characterization, and electrochemical results."""
    st.subheader("8. Laboratory Experiment Entry & Data Logging")
    st.caption("Record actual synthesis parameters, characterization measurements, and electrochemical test results for the active HE-LMFP candidate.")

    if formula is None:
        st.error("❌ **Experiment Entry Blocked**: Material design has invalid M2 site occupancy. Adjust host composition/dopants to 1.0000 first.")
        return None

    # Load or initialize experiment
    exp_id_default = current_exp.experiment_id if current_exp else f"EXP-{int(pd.Timestamp.now().timestamp())}"
    sample_id_default = current_exp.sample_id if current_exp else f"SMP-HE-{int(pd.Timestamp.now().timestamp() % 10000):04d}"
    operator_default = current_exp.operator if current_exp else "Lead Researcher"
    batch_id_default = current_exp.batch_id if current_exp else "BATCH-001"
    notes_default = current_exp.notes if current_exp else ""

    st.markdown("##### 1. Experiment Metadata")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        exp_id = st.text_input("Experiment ID", value=exp_id_default, key="lab_exp_id")
    with col2:
        sample_id = st.text_input("Sample ID", value=sample_id_default, key="lab_sample_id")
    with col3:
        operator = st.text_input("Researcher / Operator", value=operator_default, key="lab_operator")
    with col4:
        batch_id = st.text_input("Batch ID", value=batch_id_default, key="lab_batch_id")

    notes = st.text_area("Experiment Notes & Context", value=notes_default, key="lab_notes")

    exp = LabExperiment(
        experiment_id=exp_id,
        sample_id=sample_id,
        created_at=current_exp.created_at if current_exp else pd.Timestamp.now().isoformat(),
        updated_at=pd.Timestamp.now().isoformat(),
        operator=operator,
        batch_id=batch_id,
        notes=notes,
        status=current_exp.status if current_exp else ExperimentStatus.DESIGNED,
        generated_formula=formula.formula_string,
        mn_frac=mn_frac,
        fe_frac=fe_frac,
        dopants=dopants,
        carbon_wt_pct=mod_specs.carbon_coating_wt_pct,
        cnt_wt_pct=mod_specs.cnt_wt_pct,
        mgo_enabled=mod_specs.mgo_enabled,
        synthesis_route="Co-precipitation",
        synthesis_data=current_exp.synthesis_data if current_exp else None,
        characterization_data=current_exp.characterization_data if current_exp else None,
        electrochemical_data=current_exp.electrochemical_data if current_exp else None
    )

    tab_syn, tab_char, tab_elec = st.tabs(["Actual Synthesis Entry", "Actual Characterization Entry", "Actual Electrochemical Testing Entry"])

    with tab_syn:
        st.markdown("##### 🧪 Actual Synthesis Processing Parameters")
        st.caption("Distinguish PLANNED parameters from EXPERIMENTAL laboratory measurements.")
        syn_data = exp.synthesis_data or ActualSynthesisData()

        col_a, col_b = st.columns(2)
        with col_a:
            metal_prec = st.text_input("Actual Precursors Used", value=syn_data.metal_precursors or "", key="syn_prec")
            prec_mass = st.number_input("Total Precursor Mass (g)", value=float(syn_data.precursor_mass_g or 0.0), step=1.0, format="%.2f", key="syn_mass")
            precip_agent = st.text_input("Actual Precipitating Agent", value=syn_data.precipitating_agent or "", key="syn_agent")
            ph = st.number_input("Actual Reaction pH", value=float(syn_data.reaction_ph or 0.0), step=0.1, format="%.2f", key="syn_ph")
            rxn_temp = st.number_input("Actual Reaction Temp (°C)", value=float(syn_data.reaction_temp_c or 0.0), step=5.0, format="%.1f", key="syn_temp")
        with col_b:
            rxn_time = st.number_input("Actual Reaction Time (h)", value=float(syn_data.reaction_time_h or 0.0), step=0.5, format="%.1f", key="syn_time")
            calc_temp = st.number_input("Actual Calcination Temp (°C)", value=float(syn_data.calcination_temp_c or 0.0), step=10.0, format="%.1f", key="syn_calc_temp")
            calc_dur = st.number_input("Actual Calcination Duration (h)", value=float(syn_data.calcination_duration_h or 0.0), step=0.5, format="%.1f", key="syn_calc_dur")
            calc_atmos = st.text_input("Actual Calcination Atmosphere", value=syn_data.calcination_atmosphere or "Ar/H2 (95/5)", key="syn_atmos")
            yield_p = st.number_input("Actual Yield (%)", value=float(syn_data.yield_pct or 0.0), step=1.0, format="%.1f", key="syn_yield")

        obs = st.text_area("Synthesis Observations", value=syn_data.observations or "", key="syn_obs")

        if any([metal_prec, prec_mass > 0, precip_agent, ph > 0, rxn_temp > 0, calc_temp > 0, yield_p > 0, obs]):
            exp.synthesis_data = ActualSynthesisData(
                metal_precursors=metal_prec or None,
                precursor_mass_g=prec_mass if prec_mass > 0 else None,
                precipitating_agent=precip_agent or None,
                reaction_ph=ph if ph > 0 else None,
                reaction_temp_c=rxn_temp if rxn_temp > 0 else None,
                reaction_time_h=rxn_time if rxn_time > 0 else None,
                calcination_temp_c=calc_temp if calc_temp > 0 else None,
                calcination_duration_h=calc_dur if calc_dur > 0 else None,
                calcination_atmosphere=calc_atmos or None,
                yield_pct=yield_p if yield_p > 0 else None,
                observations=obs or None
            )

    with tab_char:
        st.markdown("##### 🔬 Actual Characterization Results (XRD / SEM / BET / Conductivity)")
        char_data = exp.characterization_data or ActualCharacterizationData()

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            xrd_purity = st.number_input("XRD Phase Purity (%)", value=float(char_data.xrd_phase_purity_pct or 0.0), step=0.5, format="%.1f", key="char_xrd_purity")
            lat_a = st.number_input("Lattice Parameter a (Å)", value=float(char_data.lattice_param_a or 0.0), step=0.001, format="%.4f", key="char_lat_a")
            lat_b = st.number_input("Lattice Parameter b (Å)", value=float(char_data.lattice_param_b or 0.0), step=0.001, format="%.4f", key="char_lat_b")
            lat_c = st.number_input("Lattice Parameter c (Å)", value=float(char_data.lattice_param_c or 0.0), step=0.001, format="%.4f", key="char_lat_c")
            vol = st.number_input("Unit Cell Volume (Å³)", value=float(char_data.unit_cell_volume or 0.0), step=0.1, format="%.2f", key="char_vol")
            impurity = st.text_input("Observed Impurity Phases", value=char_data.impurity_phases or "None", key="char_impurity")
        with col_c2:
            antisite = st.number_input("Li/Mn Antisite Defects (%)", value=float(char_data.antisite_defects_pct or 0.0), step=0.1, format="%.2f", key="char_antisite")
            sem_morph = st.text_input("SEM Particle Morphology", value=char_data.sem_morphology or "Spherical primary nanoparticles", key="char_sem")
            part_size = st.number_input("Average Particle Size (nm)", value=float(char_data.particle_size_nm or 0.0), step=10.0, format="%.1f", key="char_psize")
            bet_sa = st.number_input("BET Surface Area (m²/g)", value=float(char_data.bet_surface_area_m2g or 0.0), step=0.5, format="%.2f", key="char_bet")
            elec_cond = st.number_input("Electrical Conductivity (S/cm)", value=float(char_data.electrical_conductivity_scm or 0.0), format="%.2e", key="char_cond")
            tap_dens = st.number_input("Tap Density (g/cm³)", value=float(char_data.tap_density_gcm3 or 0.0), step=0.05, format="%.2f", key="char_tap")

        char_notes = st.text_area("Characterization Notes", value=char_data.notes or "", key="char_notes")

        if any([xrd_purity > 0, lat_a > 0, bet_sa > 0, elec_cond > 0, tap_dens > 0, char_notes]):
            exp.characterization_data = ActualCharacterizationData(
                xrd_phase_purity_pct=xrd_purity if xrd_purity > 0 else None,
                lattice_param_a=lat_a if lat_a > 0 else None,
                lattice_param_b=lat_b if lat_b > 0 else None,
                lattice_param_c=lat_c if lat_c > 0 else None,
                unit_cell_volume=vol if vol > 0 else None,
                impurity_phases=impurity or None,
                antisite_defects_pct=antisite if antisite > 0 else None,
                sem_morphology=sem_morph or None,
                particle_size_nm=part_size if part_size > 0 else None,
                bet_surface_area_m2g=bet_sa if bet_sa > 0 else None,
                electrical_conductivity_scm=elec_cond if elec_cond > 0 else None,
                tap_density_gcm3=tap_dens if tap_dens > 0 else None,
                notes=char_notes or None
            )

    with tab_elec:
        st.markdown("##### ⚡ Actual Electrochemical Test Measurements")
        elec_data = exp.electrochemical_data or ActualElectrochemicalData()

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            c_002 = st.number_input("0.02C Discharge Capacity (mAh/g)", value=float(elec_data.cap_0_02c or 0.0), step=1.0, format="%.1f", key="elec_c002")
            c_01 = st.number_input("0.1C Discharge Capacity (mAh/g)", value=float(elec_data.cap_0_1c or 0.0), step=1.0, format="%.1f", key="elec_c01")
            c_1 = st.number_input("1.0C Discharge Capacity (mAh/g)", value=float(elec_data.cap_1c or 0.0), step=1.0, format="%.1f", key="elec_c1")
            c_2 = st.number_input("2.0C Discharge Capacity (mAh/g)", value=float(elec_data.cap_2c or 0.0), step=1.0, format="%.1f", key="elec_c2")
            c_4 = st.number_input("4.0C Discharge Capacity (mAh/g)", value=float(elec_data.cap_4c or 0.0), step=1.0, format="%.1f", key="elec_c4")
            ice = st.number_input("Initial Coulombic Efficiency (%)", value=float(elec_data.initial_coulombic_efficiency or 0.0), step=0.5, format="%.1f", key="elec_ice")
        with col_e2:
            ret_gen = st.number_input("Overall Capacity Retention (%)", value=float(elec_data.capacity_retention_pct or 0.0), step=0.5, format="%.1f", key="elec_ret_gen")
            ret_25 = st.number_input("Room-Temp (25°C) Retention (%)", value=float(elec_data.retention_25c_pct or 0.0), step=0.5, format="%.1f", key="elec_ret_25")
            ret_55 = st.number_input("High-Temp (55°C) Retention (%)", value=float(elec_data.retention_55c_pct or 0.0), step=0.5, format="%.1f", key="elec_ret_55")
            ret_m20 = st.number_input("Low-Temp (-20°C) Retention (%)", value=float(elec_data.retention_minus20c_pct or 0.0), step=0.5, format="%.1f", key="elec_ret_m20")
            cycles = st.number_input("Cycle Life (Cycles Tested)", value=int(elec_data.cycle_life_cycles or 0), step=50, key="elec_cycles")

        elec_notes = st.text_area("Electrochemical Testing Notes", value=elec_data.notes or "", key="elec_notes")

        if any([c_01 > 0, c_1 > 0, ice > 0, ret_25 > 0, ret_55 > 0, ret_m20 > 0, elec_notes]):
            exp.electrochemical_data = ActualElectrochemicalData(
                cap_0_02c=c_002 if c_002 > 0 else None,
                cap_0_1c=c_01 if c_01 > 0 else None,
                cap_1c=c_1 if c_1 > 0 else None,
                cap_2c=c_2 if c_2 > 0 else None,
                cap_4c=c_4 if c_4 > 0 else None,
                voltage_min=2.5,
                voltage_max=4.2,
                initial_discharge_cap=c_01 if c_01 > 0 else None,
                initial_coulombic_efficiency=ice if ice > 0 else None,
                cycle_life_cycles=cycles if cycles > 0 else None,
                capacity_retention_pct=ret_gen if ret_gen > 0 else None,
                retention_25c_pct=ret_25 if ret_25 > 0 else None,
                retention_55c_pct=ret_55 if ret_55 > 0 else None,
                retention_minus20c_pct=ret_m20 if ret_m20 > 0 else None,
                notes=elec_notes or None
            )

    exp.update_status_automatically()

    col_save1, col_save2 = st.columns([1, 3])
    db_info = get_database_mode_info()
    is_cloud = db_info.get("mode") == "CLOUD_MODE"
    btn_label = "💾 Save Record to Supabase" if is_cloud else "💾 Save Record to SQLite"
    db_target_name = "PostgreSQL / Supabase cloud database" if is_cloud else "local SQLite database"

    with col_save1:
        if st.button(btn_label, use_container_width=True):
            val_rep = validate_lab_experiment(exp)
            if not val_rep.is_valid:
                for err in val_rep.errors:
                    st.error(f"❌ {err}")
            else:
                save_experiment(exp)
                st.success(f"✅ Experiment `{exp.experiment_id}` ({exp.status.value}) saved successfully to {db_target_name}!")
                if val_rep.warnings:
                    for warn in val_rep.warnings:
                        st.warning(f"⚠️ {warn}")

    with col_save2:
        st.info(f"📌 Current Experiment Status: **{exp.status.value}** | Active Formula: `{exp.generated_formula}`")

    return exp


def render_experimental_comparison_section(comp_matrix: ComparisonMatrix):
    """Render triple comparison matrix between Computational Design, Literature, and Actual Experiment."""
    st.subheader("9. Computational vs Literature vs Actual Experiment Validation Matrix")
    st.caption("Explicit comparison across CALCULATED (V1 Engine), LITERATURE_REPORTED (V2 Database), and EXPERIMENTAL (Lab Entries).")

    st.markdown(f"**Target Formula**: `{comp_matrix.formula_string}` | **Literature Match Status**: `{comp_matrix.literature_match_status}`")

    table_data = []
    for row in comp_matrix.rows:
        calc_str = f"{row.calculated_val:.1f} {row.unit}" if row.calculated_val is not None else "N/A"
        lit_str = f"{row.literature_val:.1f} {row.unit}" if row.literature_val is not None else "N/A"
        exp_str = f"{row.experimental_val:.1f} {row.unit}" if row.experimental_val is not None else "Not Measured"

        res_calc_str = f"{row.residual_vs_calculated:+.1f} {row.unit}" if row.residual_vs_calculated is not None else "N/A"
        res_lit_str = f"{row.residual_vs_literature:+.1f} {row.unit}" if row.residual_vs_literature is not None else "N/A"

        table_data.append({
            "Property / Metric": row.property_name,
            "Unit": row.unit,
            "CALCULATED (V1 Engine)": calc_str,
            "LITERATURE_REPORTED (V2)": lit_str,
            "EXPERIMENTAL (Lab Data)": exp_str,
            "Residual (Exp - Calc)": res_calc_str,
            "Residual (Exp - Lit)": res_lit_str,
            "Context": row.notes
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.info(comp_matrix.summary_notes)


def render_saved_experiments_database_section():
    """Render interactive database explorer for viewing, loading, searching, and exporting saved lab experiments."""
    st.subheader("10. Saved Laboratory Experiments Database")

    db_info = get_database_mode_info()
    if db_info.get("mode") == "CLOUD_MODE":
        st.caption("🟢 **CLOUD MODE — PostgreSQL / Supabase** (Shared Persistent Storage)")
    else:
        st.caption("🔵 **LOCAL MODE — SQLite** (`data/lab_experiments.db`)")

    experiments = list_experiments()
    if not experiments:
        st.info("ℹ️ No laboratory experiments recorded yet in the active database backend.")
        return

    st.markdown(f"Total Stored Experiments: **{len(experiments)}** records")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📥 Export All Experiments to CSV", use_container_width=True):
            csv_file = export_experiments_to_csv()
            st.success(f"✅ Exported to `{csv_file}`")
    with col_btn2:
        if st.button("📥 Export All Experiments to JSON", use_container_width=True):
            json_file = export_experiments_to_json()
            st.success(f"✅ Exported to `{json_file}`")

    table_data = []
    for exp in experiments:
        elec = exp.electrochemical_data
        table_data.append({
            "Experiment ID": exp.experiment_id,
            "Sample ID": exp.sample_id,
            "Status": exp.status.value,
            "Updated At": exp.updated_at[:19].replace("T", " "),
            "Operator": exp.operator,
            "Batch ID": exp.batch_id,
            "Generated Formula": exp.generated_formula,
            "0.1C Cap (mAh/g)": f"{elec.cap_0_1c:.1f}" if elec and elec.cap_0_1c else "N/A",
            "25°C Ret (%)": f"{elec.retention_25c_pct:.1f}" if elec and elec.retention_25c_pct else "N/A",
            "55°C Ret (%)": f"{elec.retention_55c_pct:.1f}" if elec and elec.retention_55c_pct else "N/A",
            "-20°C Ret (%)": f"{elec.retention_minus20c_pct:.1f}" if elec and elec.retention_minus20c_pct else "N/A",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    col_del1, col_del2 = st.columns([2, 1])
    with col_del1:
        del_exp_id = st.selectbox("Select Experiment to Delete:", options=[e.experiment_id for e in experiments], key="del_exp_select")
    with col_del2:
        if st.button("🗑️ Delete Selected Experiment", use_container_width=True):
            if delete_experiment(del_exp_id):
                st.success(f"Deleted experiment `{del_exp_id}`.")
                st.rerun()


def render_ml_prediction_section(
    formula: Optional[ChemicalFormula],
    mn_frac: float,
    fe_frac: float,
    dopants: List[Dict[str, Any]],
    mod_specs: MaterialModifications,
    cb_result: Optional[ChargeBalanceResult] = None
):
    """Render interactive literature-based ML performance prediction section."""
    st.subheader("10. 🧠 Literature-Based ML Performance Prediction")
    st.caption("Random Forest regression models trained on quality-filtered observations from 1,215 literature sample records.")

    st.markdown("""
    > 📌 **Data Category Classification**:
    > - 🔬 **LITERATURE-REPORTED**: Records matched from reference literature dataset.
    > - ⚖️ **CALCULATED BY CHEMISTRY ENGINE**: Deterministic stoichiometry, configurational entropy ($S_{config}/R$), theoretical capacity ($Q_{theo}$).
    > - 🧠 **ML PREDICTED**: Empirical Random Forest regression predictions trained via paper-level `GroupKFold` cross-validation.
    > - 🧪 **EXPERIMENTALLY VALIDATED**: Verified lab test results logged in local SQLite database.
    """)

    if formula is None or (cb_result and not cb_result.m2_occupancy_valid):
        st.error("❌ **ML Prediction Blocked**: Chemical formula generation is blocked because M2 site occupancy sum does not equal 1.0000.")
        return

    st.warning("⚠️ **Literature-trained ML prediction — not experimentally validated by ECMT.**")

    carbon_wt = mod_specs.carbon_coating_wt_pct if mod_specs.carbon_coating_enabled else 0.0
    res = predict_composition_performance(
        mn_ratio=mn_frac,
        fe_ratio=fe_frac,
        dopants=dopants,
        carbon_wt=carbon_wt,
        molar_mass=formula.molar_mass if formula else 157.7
    )

    for warn in res.get("coverage_warnings", []):
        st.warning(f"⚠️ {warn}")

    st.markdown(f"#### Active Composition: `{formula.formula_string}`")
    st.caption(f"Mn: `{mn_frac:.4f}` | Fe: `{fe_frac:.4f}` | Dopants: `{len(dopants)}` elements | Carbon Coating: `{carbon_wt:.2f} wt%`")

    preds = res.get("predictions", {})

    st.markdown("##### Predicted Electrochemical Performance & Uncertainty")
    col1, col2, col3, col4 = st.columns(4)

    t_01c = preds.get("0_1C_capacity", {})
    t_1c = preds.get("1C_capacity", {})
    t_5c = preds.get("5C_capacity", {})
    t_ret = preds.get("capacity_retention", {})

    with col1:
        if t_01c.get("status") == "trained":
            val = t_01c.get("predicted_value", 0.0)
            std = t_01c.get("std_uncertainty", 0.0)
            st.metric(
                label="0.1C Discharge Capacity",
                value=f"{val:.1f} mAh/g",
                delta=f"± {std:.1f} mAh/g (std dev)",
                delta_color="off"
            )
        else:
            st.error("0.1C Capacity: Insufficient literature data")

    with col2:
        if t_1c.get("status") == "trained":
            val = t_1c.get("predicted_value", 0.0)
            std = t_1c.get("std_uncertainty", 0.0)
            st.metric(
                label="1.0C Discharge Capacity",
                value=f"{val:.1f} mAh/g",
                delta=f"± {std:.1f} mAh/g (std dev)",
                delta_color="off"
            )
        else:
            st.error("1C Capacity: Insufficient literature data")

    with col3:
        if t_5c.get("status") == "trained":
            val = t_5c.get("predicted_value", 0.0)
            std = t_5c.get("std_uncertainty", 0.0)
            st.metric(
                label="5.0C Discharge Capacity",
                value=f"{val:.1f} mAh/g",
                delta=f"± {std:.1f} mAh/g (std dev)",
                delta_color="off"
            )
        else:
            st.error("5C Capacity: Insufficient literature data")

    with col4:
        if t_ret.get("status") == "trained":
            val = t_ret.get("predicted_value", 0.0)
            std = t_ret.get("std_uncertainty", 0.0)
            st.metric(
                label="Capacity Retention",
                value=f"{val:.1f} %",
                delta=f"± {std:.1f} % (std dev)",
                delta_color="off"
            )
        else:
            st.error("Capacity Retention: Insufficient literature data")

    st.markdown("##### Additional Electrochemical Targets Data Coverage")
    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        t_005c = preds.get("0_05C_capacity", {})
        st.warning(f"🔸 **0.05C Discharge Capacity**: {t_005c.get('message', 'Insufficient literature data for reliable ML model.')} ({t_005c.get('sample_count', 0)} samples in DB)")
    with col_sub2:
        t_ice = preds.get("initial_ice", {})
        st.warning(f"🔸 **Initial Coulombic Efficiency (ICE)**: {t_ice.get('message', 'Insufficient literature data for reliable ML model.')} ({t_ice.get('sample_count', 0)} samples in DB)")

    with st.expander("📊 Model Validation Metrics & Training Metadata (GroupKFold Cross-Validation by Paper)", expanded=False):
        meta_rows = []
        for tk, tm in preds.items():
            if tm.get("status") == "trained":
                m = tm.get("metrics", {})
                meta_rows.append({
                    "Electrochemical Target": tm.get("label"),
                    "Unit": tm.get("unit"),
                    "Status": "Trained",
                    "Training Observations": tm.get("sample_count"),
                    "Papers Represented": tm.get("paper_count"),
                    "CV MAE": f"{m.get('mae', 0.0):.2f} ± {m.get('mae_std', 0.0):.2f}",
                    "CV RMSE": f"{m.get('rmse', 0.0):.2f} ± {m.get('rmse_std', 0.0):.2f}",
                    "CV R²": f"{m.get('r2', 0.0):.3f} ± {m.get('r2_std', 0.0):.3f}"
                })
            else:
                meta_rows.append({
                    "Electrochemical Target": tm.get("label"),
                    "Unit": tm.get("unit"),
                    "Status": "Skipped (Insufficient Data)",
                    "Training Observations": tm.get("sample_count"),
                    "Papers Represented": tm.get("paper_count"),
                    "CV MAE": "N/A",
                    "CV RMSE": "N/A",
                    "CV R²": "N/A"
                })
        st.dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True)
        st.caption(f"Validation Strategy: **{res['metadata']['validation_strategy']}** | Total Literature Records: **{res['metadata']['total_literature_records']}** | Total Unique Papers: **{res['metadata']['total_papers']}**")


def render_ml_placeholder_section():
    """Alias for backwards compatibility."""
    st.info("ℹ️ ML module active. Select section '10. 🧠 ML Prediction' from sidebar.")


