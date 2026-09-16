"""
Chemical Formula Generator Engine for High-Entropy Doped LMFP Materials.

Programmatically generates formatted chemical formulas, computes exact formula 
molar masses, and formats site occupancy breakdowns.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from .dopants import HOST_ELEMENTS, DOPANT_DATABASE

@dataclass
class FormulaComponent:
    element: str
    site: str
    fraction: float
    oxidation_state: int
    charge_contribution: float
    atomic_weight: float

@dataclass
class ChemicalFormula:
    formula_string: str
    formula_html: str
    formula_latex: str
    molar_mass: float
    li_fraction: float
    mn_fraction: float
    fe_fraction: float
    dopants: List[FormulaComponent]
    components: List[FormulaComponent]
    m2_occupancy: float
    s_si: float
    gamma_f: float

def _format_subscript(val: float, digits: int = 4) -> str:
    """Format float for formula subscript string, omitting 1.0 or trailing zeros."""
    if abs(val - 1.0) < 1e-5:
        return ""
    val_str = f"{val:.{digits}f}".rstrip('0').rstrip('.')
    return val_str

def _format_html_subscript(val: float, digits: int = 4) -> str:
    sub = _format_subscript(val, digits)
    return f"<sub>{sub}</sub>" if sub else ""

def _format_latex_subscript(val: float, digits: int = 4) -> str:
    sub = _format_subscript(val, digits)
    return f"_{{{sub}}}" if sub else ""

def generate_formula(
    li_frac: float,
    mn_frac: float,
    fe_frac: float,
    dopants_input: List[Dict[str, Any]], # list of {"symbol": str, "fraction": float, "oxidation_state": int}
    s_si: float = 0.0,
    gamma_f: float = 0.0
) -> ChemicalFormula:
    """
    Generate chemical formula object for HE-LMFP.
    
    Formula General Template:
    Li_(1-delta) [ Mn_m Fe_f Dop1_x1 Dop2_x2 ... ] P_(1-s) Si_s O_(4-gamma) F_gamma
    """
    components = []
    
    # Li component
    li_aw = HOST_ELEMENTS["Li"]["atomic_weight"]
    components.append(FormulaComponent(
        element="Li",
        site="Li-site",
        fraction=li_frac,
        oxidation_state=1,
        charge_contribution=li_frac * 1.0,
        atomic_weight=li_aw
    ))
    
    # Mn component
    mn_aw = HOST_ELEMENTS["Mn"]["atomic_weight"]
    components.append(FormulaComponent(
        element="Mn",
        site="M2",
        fraction=mn_frac,
        oxidation_state=2,
        charge_contribution=mn_frac * 2.0,
        atomic_weight=mn_aw
    ))
    
    # Fe component
    fe_aw = HOST_ELEMENTS["Fe"]["atomic_weight"]
    components.append(FormulaComponent(
        element="Fe",
        site="M2",
        fraction=fe_frac,
        oxidation_state=2,
        charge_contribution=fe_frac * 2.0,
        atomic_weight=fe_aw
    ))
    
    # Dopant components
    dopant_objs = []
    dopant_m2_sum = 0.0
    for d in dopants_input:
        sym = d["symbol"]
        frac = d["fraction"]
        ox = d["oxidation_state"]
        aw = DOPANT_DATABASE.get(sym, {}).get("atomic_weight", 0.0)
        
        comp = FormulaComponent(
            element=sym,
            site="M2",
            fraction=frac,
            oxidation_state=ox,
            charge_contribution=frac * ox,
            atomic_weight=aw
        )
        dopant_objs.append(comp)
        components.append(comp)
        dopant_m2_sum += frac
        
    m2_occupancy = mn_frac + fe_frac + dopant_m2_sum
    
    # P and Si
    p_frac = 1.0 - s_si
    p_aw = HOST_ELEMENTS["P"]["atomic_weight"]
    components.append(FormulaComponent(
        element="P",
        site="P-site",
        fraction=p_frac,
        oxidation_state=5,
        charge_contribution=p_frac * 5.0,
        atomic_weight=p_aw
    ))
    
    if s_si > 0.0:
        si_aw = HOST_ELEMENTS["Si"]["atomic_weight"]
        components.append(FormulaComponent(
            element="Si",
            site="P-site",
            fraction=s_si,
            oxidation_state=4,
            charge_contribution=s_si * 4.0,
            atomic_weight=si_aw
        ))
        
    # O and F
    o_frac = 4.0 - gamma_f
    o_aw = HOST_ELEMENTS["O"]["atomic_weight"]
    components.append(FormulaComponent(
        element="O",
        site="Anion-site",
        fraction=o_frac,
        oxidation_state=-2,
        charge_contribution=o_frac * -2.0,
        atomic_weight=o_aw
    ))
    
    if gamma_f > 0.0:
        f_aw = HOST_ELEMENTS["F"]["atomic_weight"]
        components.append(FormulaComponent(
            element="F",
            site="Anion-site",
            fraction=gamma_f,
            oxidation_state=-1,
            charge_contribution=gamma_f * -1.0,
            atomic_weight=f_aw
        ))
        
    # Total Molar Mass (g/mol)
    molar_mass = sum(c.fraction * c.atomic_weight for c in components)
    
    # Construct formula strings
    li_sub = _format_subscript(li_frac)
    mn_sub = _format_subscript(mn_frac)
    fe_sub = _format_subscript(fe_frac)
    
    m2_parts = [f"Mn{mn_sub}", f"Fe{fe_sub}"]
    for d in dopant_objs:
        d_sub = _format_subscript(d.fraction)
        m2_parts.append(f"{d.element}{d_sub}")
        
    m2_str = "".join(m2_parts)
    
    p_sub = _format_subscript(p_frac)
    p_str = f"P{p_sub}" if p_frac > 0 else ""
    if s_si > 0:
        si_sub = _format_subscript(s_si)
        p_str += f"Si{si_sub}"
        
    o_sub = _format_subscript(o_frac)
    anion_str = f"O{o_sub}"
    if gamma_f > 0:
        f_sub = _format_subscript(gamma_f)
        anion_str += f"F{f_sub}"
        
    formula_string = f"Li{li_sub}[{m2_str}]{p_str}{anion_str}"
    
    # HTML string
    li_html = _format_html_subscript(li_frac)
    mn_html = _format_html_subscript(mn_frac)
    fe_html = _format_html_subscript(fe_frac)
    m2_html_parts = [f"Mn{mn_html}", f"Fe{fe_html}"]
    for d in dopant_objs:
        d_html = _format_html_subscript(d.fraction)
        m2_html_parts.append(f"{d.element}{d_html}")
    m2_html_str = "".join(m2_html_parts)
    
    p_html = f"P{_format_html_subscript(p_frac)}" if p_frac > 0 else ""
    if s_si > 0:
        p_html += f"Si{_format_html_subscript(s_si)}"
    o_html = f"O{_format_html_subscript(o_frac)}"
    if gamma_f > 0:
        o_html += f"F{_format_html_subscript(gamma_f)}"
        
    formula_html = f"Li{li_html}[{m2_html_str}]{p_html}{o_html}"
    
    # Latex string
    li_latex = _format_latex_subscript(li_frac)
    mn_latex = _format_latex_subscript(mn_frac)
    fe_latex = _format_latex_subscript(fe_frac)
    m2_latex_parts = [f"\\text{{Mn}}{mn_latex}", f"\\text{{Fe}}{fe_latex}"]
    for d in dopant_objs:
        d_latex = _format_latex_subscript(d.fraction)
        m2_latex_parts.append(f"\\text{{{d.element}}}{d_latex}")
    m2_latex_str = "".join(m2_latex_parts)
    
    p_latex = f"\\text{{P}}{_format_latex_subscript(p_frac)}" if p_frac > 0 else ""
    if s_si > 0:
        p_latex += f"\\text{{Si}}{_format_latex_subscript(s_si)}"
    o_latex = f"\\text{{O}}{_format_latex_subscript(o_frac)}"
    if gamma_f > 0:
        o_latex += f"\\text{{F}}{_format_latex_subscript(gamma_f)}"
        
    formula_latex = f"\\text{{Li}}{li_latex}[{m2_latex_str}]{p_latex}{o_latex}"

    return ChemicalFormula(
        formula_string=formula_string,
        formula_html=formula_html,
        formula_latex=formula_latex,
        molar_mass=round(molar_mass, 4),
        li_fraction=round(li_frac, 6),
        mn_fraction=round(mn_frac, 6),
        fe_fraction=round(fe_frac, 6),
        dopants=dopant_objs,
        components=components,
        m2_occupancy=round(m2_occupancy, 6),
        s_si=s_si,
        gamma_f=gamma_f
    )
