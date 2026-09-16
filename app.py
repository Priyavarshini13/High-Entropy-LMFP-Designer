"""
Main Streamlit Application File for HE-LMFP Designer.

High-Entropy Doped LMFP Formula & Materials Design Platform.
Integrates V1 Deterministic Chemistry Engine, V2 Literature Reference Engine,
and Laboratory Experiment & Experimental Validation Engine with Left Sidebar Workflow Navigation.
"""

import streamlit as st

# Set Streamlit Page Config as first command
st.set_page_config(
    page_title="HE-LMFP Designer - High-Entropy Doped LMFP Platform",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

from chemistry.charge_balance import calculate_charge_balance
from chemistry.formula import generate_formula
from chemistry.entropy import calculate_configurational_entropy
from chemistry.capacity import calculate_capacity_metrics
from chemistry.validation import validate_composition
from literature.loader import load_literature_database
from literature.matcher import match_composition
from experiments.comparison import generate_comparison_matrix
from design.modifications import get_material_modifications
from design.processing import get_coprecipitation_processing
from ui.components import (
    render_header,
    render_host_composition_section,
    render_dopant_selection_section,
    render_charge_balance_section,
    render_formula_card,
    render_entropy_section,
    render_literature_section,
    render_capacity_section,
    render_modifications_section,
    render_synthesis_section,
    render_characterization_section,
    render_validation_section,
    render_report_section,
    render_lab_experiment_entry_section,
    render_experimental_comparison_section,
    render_saved_experiments_database_section,
    render_ml_prediction_section,
    render_ml_placeholder_section
)


@st.cache_data
def get_cached_literature_db():
    return load_literature_database()


def main():
    render_header()
    
    # Load literature reference database
    lit_db = get_cached_literature_db()
    
    # Left Sidebar Primary Workflow Navigation
    st.sidebar.title("HE-LMFP Designer")
    st.sidebar.markdown("### WORKFLOW NAVIGATION")
    
    nav_options = [
        "🧬 Design",
        "⚖️ Chemistry Validation",
        "📊 Entropy & Capacity",
        "📚 Literature Audit",
        "🔬 Synthesis Plan",
        "🔎 Characterization Plan",
        "🧪 Lab Experiment Entry",
        "📈 Experimental Comparison",
        "💾 Saved Experiments DB",
        "🧠 Optimization / ML",
        "📄 Final Report"
    ]
    
    selected_section = st.sidebar.radio(
        "Select Workflow Section:",
        options=nav_options,
        index=0,
        key="sidebar_workflow_nav"
    )
    
    st.sidebar.divider()
    st.sidebar.markdown(f"""
    **Core Engine Status:**
    - Deterministic V1 Chemistry Engine
    - Multi-Element High-Entropy M2 Site Doping
    - Automatic Charge Balancing ($\text{{Li}}$ vacancies $\delta$)
    - Verified Literature Audit ({len(lit_db)} Records)
    - Co-precipitation Synthesis Protocol
    - Laboratory Experiment Storage (SQLite)
    """)
    
    # Default Reference Composition: Li(Mn0.65 Fe0.26 Mg0.02 Zn0.02 Nb0.01 Cu0.02 Zr0.02)PO4
    default_dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
    ]
    
    # Session State Initialization for Composition Inputs
    if "mn_frac" not in st.session_state:
        st.session_state["mn_frac"] = 0.65
    if "fe_frac" not in st.session_state:
        st.session_state["fe_frac"] = 0.26
    if "dopants_input" not in st.session_state:
        st.session_state["dopants_input"] = default_dopants

    # Active Section View Rendering
    if selected_section == "🧬 Design":
        mn_frac, fe_frac = render_host_composition_section(
            mn_default=st.session_state["mn_frac"],
            fe_default=st.session_state["fe_frac"]
        )
        st.divider()
        dopants_input = render_dopant_selection_section(st.session_state["dopants_input"])
        st.session_state["mn_frac"] = mn_frac
        st.session_state["fe_frac"] = fe_frac
        st.session_state["dopants_input"] = dopants_input
    else:
        mn_frac = st.session_state["mn_frac"]
        fe_frac = st.session_state["fe_frac"]
        dopants_input = st.session_state["dopants_input"]

    # Chemistry Calculation Pipeline (Deterministic V1 Engine)
    cb_result = calculate_charge_balance(mn_frac, fe_frac, dopants_input, strategy="ADJUST_LI")
    
    # Enforce M2 Occupancy Gate (Total M2 occupancy must equal 1.0000)
    if cb_result.m2_occupancy_valid:
        formula = generate_formula(cb_result.adjusted_li, mn_frac, fe_frac, dopants_input)
        entropy_res = calculate_configurational_entropy(mn_frac, fe_frac, dopants_input)
        cap_metrics = calculate_capacity_metrics(cb_result.adjusted_li, formula.molar_mass)
        match_res = match_composition(formula, lit_db)
    else:
        formula = None
        entropy_res = None
        cap_metrics = None
        match_res = None

    # Render Synthesis & Modifications Parameters or Load Defaults
    if selected_section == "🔬 Synthesis Plan":
        mod_specs = render_modifications_section()
        st.divider()
        synth_specs = render_synthesis_section()
        st.session_state["mod_specs"] = mod_specs
        st.session_state["synth_specs"] = synth_specs
    else:
        mod_specs = st.session_state.get("mod_specs", get_material_modifications("Carbon Coating Only", 2.5, 1.0, False))
        synth_specs = st.session_state.get("synth_specs", get_coprecipitation_processing())

    # Validation Report Calculation
    val_report = validate_composition(
        mn_frac=mn_frac,
        fe_frac=fe_frac,
        dopants=dopants_input,
        user_li=cb_result.user_li,
        is_charge_balanced=cb_result.is_balanced,
        m2_occupancy=cb_result.m2_occupancy,
        carbon_wt_pct=mod_specs.carbon_coating_wt_pct,
        carbon_enabled=mod_specs.carbon_coating_enabled,
        cnt_wt_pct=mod_specs.cnt_wt_pct,
        cnt_enabled=mod_specs.cnt_enabled,
        mgo_enabled=mod_specs.mgo_enabled,
        f_doping_enabled=False
    )

    # -------------------------------------------------------------------
    # WORKFLOW SECTION DISPLAY ROUTING
    # -------------------------------------------------------------------
    if selected_section == "🧬 Design":
        st.divider()
        render_formula_card(formula, cb_result)

    elif selected_section == "⚖️ Chemistry Validation":
        render_charge_balance_section(cb_result)
        st.divider()
        render_validation_section(val_report)

    elif selected_section == "📊 Entropy & Capacity":
        render_entropy_section(entropy_res)
        st.divider()
        render_capacity_section(cap_metrics)

    elif selected_section == "📚 Literature Audit":
        render_literature_section(match_res)

    elif selected_section == "🔬 Synthesis Plan":
        pass  # Rendered above to capture user inputs

    elif selected_section == "🔎 Characterization Plan":
        render_characterization_section()

    elif selected_section == "🧪 Lab Experiment Entry":
        current_exp = render_lab_experiment_entry_section(
            formula=formula,
            mn_frac=mn_frac,
            fe_frac=fe_frac,
            dopants=dopants_input,
            mod_specs=mod_specs
        )
        st.session_state["current_exp"] = current_exp

    elif selected_section == "📈 Experimental Comparison":
        current_exp = st.session_state.get("current_exp", None)
        comp_matrix = generate_comparison_matrix(
            formula=formula,
            cap_metrics=cap_metrics,
            match_res=match_res,
            experiment=current_exp
        )
        render_experimental_comparison_section(comp_matrix)

    elif selected_section == "💾 Saved Experiments DB":
        render_saved_experiments_database_section()

    elif selected_section in ("🧠 Optimization / ML", "🧠 ML Prediction"):
        render_ml_prediction_section(
            formula=formula,
            mn_frac=mn_frac,
            fe_frac=fe_frac,
            dopants=dopants_input,
            mod_specs=mod_specs,
            cb_result=cb_result
        )

    elif selected_section == "📄 Final Report":
        current_exp = st.session_state.get("current_exp", None)
        comp_matrix = generate_comparison_matrix(
            formula=formula,
            cap_metrics=cap_metrics,
            match_res=match_res,
            experiment=current_exp
        )
        render_report_section(
            formula=formula,
            cb_result=cb_result,
            entropy_res=entropy_res,
            cap_metrics=cap_metrics,
            mod_specs=mod_specs,
            synth_specs=synth_specs,
            val_report=val_report,
            match_res=match_res,
            experiment=current_exp,
            comp_matrix=comp_matrix
        )


if __name__ == "__main__":
    main()
