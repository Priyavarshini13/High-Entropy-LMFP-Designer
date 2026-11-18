"""
Scientific Intent Classifier and Structured Entity Extractor for LMFP Research Copilot.

Supports 18 structured scientific research intents:
- SAMPLE_PROPERTY_LOOKUP
- SAMPLE_COMPARISON
- COMPOSITION_COMPARISON
- DOPANT_ANALYSIS
- COMPOSITE_MODIFICATION_ANALYSIS
- SYNTHESIS_COMPARISON
- PRECURSOR_COMPARISON
- ELECTROCHEMICAL_PERFORMANCE_ANALYSIS
- RATE_CAPABILITY_ANALYSIS
- CYCLING_STABILITY_ANALYSIS
- CHARACTERIZATION_ANALYSIS
- CROSS_PAPER_COMPARISON
- MECHANISM_EXPLANATION
- RESEARCH_GAP_ANALYSIS
- LITERATURE_SEARCH
- EXPERIMENTAL_CONDITION_FILTER
- FOLLOW_UP_QUESTION
- OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Set

from copilot.models import ExtractedEntities, ScientificIntent, ScientificIntentPayload


# Known LMFP dopants (canonical symbols) - Fe and Mn are host cations, not dopants
LMFP_KNOWN_DOPANTS = {
    "mg": "Mg", "ti": "Ti", "nb": "Nb", "zr": "Zr", "zn": "Zn",
    "ni": "Ni", "co": "Co", "cr": "Cr", "al": "Al", "v": "V",
    "cu": "Cu", "mo": "Mo", "w": "W",
    "n/s": "N/S", "s": "S", "n": "N", "f": "F",
}

# Known paper identifiers in benchmark / repository
KNOWN_PAPERS = {
    "srep26686", "p1", "p4", "p6", "p7", "p8", "p12", "p32", "p38",
    "p48", "p59", "p67", "p71", "p84", "p86", "ref29", "ref79",
}

# Known explicit sample labels
KNOWN_SAMPLE_LABELS = {
    "sd_no3", "sd_so4", "ref29", "ref79", "c-lmfp", "n-lmfp", "lmp-c",
    "limn0.75fe0.25po4/rgo", "sample_16", "sample_17", "sample_4",
}


class ScientificIntentClassifier:
    """Scientific intent classifier and parameter extractor for LMFP research questions."""

    def extract_entities(self, query: str) -> ExtractedEntities:
        """Extract all identifiable scientific entities, numerical conditions, and materials from text."""
        clean_q = query.strip()
        lower_q = clean_q.lower()

        # 1. Extract Sample IDs and Sample Labels
        sample_labels = []
        sample_ids = []
        for match in re.finditer(r"\b(sd_no3|sd_so4|ref_?79|ref_?29|p1_c-lmfp|p1_n-lmfp|sample_\d+)\b", lower_q):
            lbl = match.group(1).replace("_", "").upper()
            if "SDNO3" in lbl:
                sample_labels.append("SD_NO3")
                sample_ids.append("srep26686_SD_NO3")
            elif "SDSO4" in lbl:
                sample_labels.append("SD_SO4")
                sample_ids.append("srep26686_SD_SO4")
            elif "REF79" in lbl:
                sample_labels.append("Ref79_LiMn0.5Fe0.5PO4_NS")
                sample_labels.append("N/S co-doped")
                sample_ids.append("Lithium_manganese_iron_phosphate_materials__Design__progress__and_challenges_Ref79_LiMn0_5Fe0_5PO4")
            elif "REF29" in lbl:
                sample_labels.append("Ref29_LiMn0.8Fe0.2PO4_Ni")
                sample_labels.append("Ni-doped")
                sample_ids.append("Lithium_manganese_iron_phosphate_materials__Design__progress__and_challenges_Ref29_LiMn0_8Fe0_2PO4_Ni")
            else:
                sample_labels.append(match.group(1))

        if re.search(r"\b(?:reference\s*\[?79\]?|ref\s*\[?79\]?)\b", lower_q):
            if "Ref79_LiMn0.5Fe0.5PO4_NS" not in sample_labels:
                sample_labels.append("Ref79_LiMn0.5Fe0.5PO4_NS")
                sample_labels.append("N/S co-doped")
                sample_ids.append("Lithium_manganese_iron_phosphate_materials__Design__progress__and_challenges_Ref79_LiMn0_5Fe0_5PO4")

        if re.search(r"\b(?:reference\s*\[?29\]?|ref\s*\[?29\]?)\b", lower_q):
            if "Ref29_LiMn0.8Fe0.2PO4_Ni" not in sample_labels:
                sample_labels.append("Ref29_LiMn0.8Fe0.2PO4_Ni")
                sample_labels.append("Ni-doped")
                sample_ids.append("Lithium_manganese_iron_phosphate_materials__Design__progress__and_challenges_Ref29_LiMn0_8Fe0_2PO4_Ni")

        # Check for composite sample mentions
        if "limn0.75fe0.25po4/rgo" in lower_q or ("rgo" in lower_q and "srep26686" in lower_q):
            sample_labels.append("LiMn0.75Fe0.25PO4/rGO")
            sample_ids.append("srep26686_LiMn0_75Fe0_25PO4_rGO")

        # 2. Extract Paper IDs
        paper_ids = []
        for pm in re.finditer(r"\b(srep26686|p\d+)\b", lower_q):
            p_found = pm.group(1).lower()
            paper_ids.append(p_found)
        # Extract .pdf filename patterns or explicit "paper <name>" mentions
        for pm in re.finditer(r"\b([a-zA-Z0-9_\-]+\.pdf)\b", lower_q):
            p_pdf = pm.group(1).lower().replace(".pdf", "")
            paper_ids.append(p_pdf)
        for pm in re.finditer(r"\bpaper\s+([a-zA-Z0-9_\-]+)\b", lower_q):
            p_named = pm.group(1).lower().replace(".pdf", "")
            if p_named not in {"the", "a", "this", "that", "these", "those", "reference", "ref"}:
                paper_ids.append(p_named)
        if re.search(r"\b(?:reference\s*\[?79\]?|ref\s*\[?79\]?|ref_?79)\b", lower_q):
            paper_ids.append("ref79")
        if re.search(r"\b(?:reference\s*\[?29\]?|ref\s*\[?29\]?|ref_?29)\b", lower_q):
            paper_ids.append("ref29")

        # 3. Extract Dopant Elements
        dopants = []
        single_letter_dopants = {
            "v": ("vanadium", ["v-doped", "v doping", "v3+", "v5+"]),
            "s": ("sulfur", ["s-doped", "s doping", "s2-"]),
            "n": ("nitrogen", ["n-doped", "n doping", "n3-"]),
            "f": ("fluorine", ["f-doped", "f doping", "f-"]),
            "w": ("tungsten", ["w-doped", "w doping", "w6+"]),
        }

        for dop_key, canon in LMFP_KNOWN_DOPANTS.items():
            if dop_key in single_letter_dopants:
                name, markers = single_letter_dopants[dop_key]
                if name in lower_q or any(m in lower_q for m in markers):
                    if canon not in dopants:
                        dopants.append(canon)
            elif dop_key == "n/s":
                if "n/s" in lower_q or "nitrogen and sulfur" in lower_q:
                    if canon not in dopants:
                        dopants.append(canon)
            elif dop_key == "co":
                # Disambiguate 'Co' (Cobalt) from 'co-' prefix (co-doping, co-doped, co-precipitation)
                if "cobalt" in lower_q or re.search(r"\bco\b(?!\s*-\s*(?:dop|precip|sinter))", lower_q):
                    if canon not in dopants:
                        dopants.append(canon)
            else:
                pattern = rf"\b{re.escape(dop_key)}(?:\d*\+?)?\b"
                if (
                    re.search(pattern, lower_q)
                    or f"{dop_key}-doped" in lower_q
                    or f"{dop_key} doping" in lower_q
                    or (dop_key == "ti" and "titanium" in lower_q)
                    or (dop_key == "mg" and "magnesium" in lower_q)
                    or (dop_key == "cr" and "chromium" in lower_q)
                    or (dop_key == "ni" and "nickel" in lower_q)
                    or (dop_key == "al" and "aluminum" in lower_q)
                ):
                    if canon not in dopants:
                        dopants.append(canon)

        # 4. Extract Chemical Formulas
        formulas = []
        formula_matches = re.findall(
            r"\bLi[0-9.]*Mn[0-9.]*Fe[0-9.]*[A-Za-z0-9_.]*PO4(?:[/\@][A-Za-z0-9_]+)?\b",
            clean_q,
        )
        formulas.extend(formula_matches)

        # 5. Extract Composite Modifications
        modifications = []
        if "rgo" in lower_q or "reduced graphene oxide" in lower_q:
            modifications.append("rGO")
        if "cnt" in lower_q or "carbon nanotube" in lower_q:
            modifications.append("CNT")
        if "/c" in lower_q or "carbon coating" in lower_q or "carbon coated" in lower_q or "carbon-coated" in lower_q:
            modifications.append("Carbon_Coating")
        if "graphene" in lower_q and "rgo" not in lower_q:
            modifications.append("Graphene")

        # 6. Extract Precursors
        precursors = []
        if any(k in lower_q for k in ["nitrate", "no3", "fe(no3)3", "mn(no3)2"]):
            precursors.append("Nitrate")
        if any(k in lower_q for k in ["sulfate", "so4", "feso4", "mnso4"]):
            precursors.append("Sulfate")
        if any(k in lower_q for k in ["acetate", "ch3coo"]):
            precursors.append("Acetate")
        if "citric acid" in lower_q:
            precursors.append("Citric_Acid")

        # 7. Extract Synthesis Methods
        synthesis_methods = []
        if "spray drying" in lower_q or "spray-drying" in lower_q or "spray-dried" in lower_q:
            synthesis_methods.append("Spray Drying")
        if "sol-gel" in lower_q or "sol gel" in lower_q:
            synthesis_methods.append("Sol-Gel")
        if "solid-state" in lower_q or "solid state" in lower_q or "ball mill" in lower_q:
            synthesis_methods.append("Solid-State")
        if "solvothermal" in lower_q:
            synthesis_methods.append("Solvothermal")
        if "hydrothermal" in lower_q:
            synthesis_methods.append("Hydrothermal")
        if "freeze-dry" in lower_q or "freeze drying" in lower_q:
            synthesis_methods.append("Freeze-Drying")

        # 8. Extract C-rates
        c_rates = []
        for cm in re.finditer(r"\b(\d+(?:\.\d+)?)\s*c\b", lower_q):
            try:
                rate_val = float(cm.group(1))
                if rate_val not in c_rates and rate_val <= 100.0:
                    c_rates.append(rate_val)
            except ValueError:
                pass

        # 9. Extract Cycle Counts
        cycle_counts = []
        for cyc_m in re.finditer(r"\b(\d{1,5})\s*(?:cycles?|cyc)\b", lower_q):
            try:
                c_num = int(cyc_m.group(1))
                if c_num not in cycle_counts and c_num >= 10:
                    cycle_counts.append(c_num)
            except ValueError:
                pass
        if "1000" in lower_q or "1,000" in lower_q:
            if 1000 not in cycle_counts:
                cycle_counts.append(1000)

        # 10. Extract Temperature
        temp_c = None
        temp_m = re.search(r"\b(\d{2,4})\s*(?:°\s*c|c\b|deg\s*c)", lower_q)
        if temp_m:
            try:
                temp_c = float(temp_m.group(1))
            except ValueError:
                pass

        # 11. Extract Voltage Window
        voltage_window = None
        vw_m = re.search(r"(\d\.\d+)\s*(?:-|to|–)\s*(\d\.\d+)\s*v\b", lower_q)
        if vw_m:
            try:
                voltage_window = (float(vw_m.group(1)), float(vw_m.group(2)))
            except ValueError:
                pass

        # 12. Extract Mass Loading
        mass_loading = None
        ml_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:mg/cm2|mg\s*cm-2)", lower_q)
        if ml_m:
            try:
                mass_loading = float(ml_m.group(1))
            except ValueError:
                pass

        # 13. Extract Measurement Types
        measurement_types = []
        if any(k in lower_q for k in ["capacity", "discharge capacity", "charge capacity", "mah/g"]):
            measurement_types.append("discharge_capacity")
        if any(k in lower_q for k in ["retention", "cycling stability", "fade", "cycle life"]):
            measurement_types.append("capacity_retention")
        if any(k in lower_q for k in ["coulombic", "ice", "irreversible capacity"]):
            measurement_types.append("coulombic_efficiency")
        if any(k in lower_q for k in ["eis", "impedance", "rct", "charge transfer resistance"]):
            measurement_types.append("eis_rct")
        if any(k in lower_q for k in ["space group", "pnma", "lattice", "crystallography", "xrd"]):
            measurement_types.append("crystallography")

        # 14. Comparison Dimensions
        comparison_dimensions = []
        if len(dopants) >= 2 or ("dop" in lower_q and ("compare" in lower_q or "vs" in lower_q)):
            comparison_dimensions.append("dopants")
        if len(precursors) >= 2 or ("precursor" in lower_q and ("compare" in lower_q or "conflict" in lower_q or "vs" in lower_q)):
            comparison_dimensions.append("precursors")
        if len(synthesis_methods) >= 2 or ("synthesis" in lower_q and ("compare" in lower_q or "vs" in lower_q)):
            comparison_dimensions.append("synthesis_methods")
        if len(c_rates) >= 2 or ("rate" in lower_q and ("compare" in lower_q or "vs" in lower_q)):
            comparison_dimensions.append("c_rates")
        if len(sample_labels) >= 2:
            comparison_dimensions.append("samples")
        if len(paper_ids) >= 2:
            comparison_dimensions.append("papers")
        if ("rgo" in lower_q or "carbon" in lower_q) and ("unmodified" in lower_q or "pristine" in lower_q or "plain" in lower_q):
            comparison_dimensions.append("modifications")

        return ExtractedEntities(
            sample_ids=list(set(sample_ids)),
            sample_labels=list(set(sample_labels)),
            paper_ids=list(set(paper_ids)),
            dopants=dopants,
            formulas=list(set(formulas)),
            modifications=list(set(modifications)),
            precursors=list(set(precursors)),
            synthesis_methods=list(set(synthesis_methods)),
            c_rates=c_rates,
            cycle_counts=cycle_counts,
            temperature_c=temp_c,
            voltage_window=voltage_window,
            mass_loading_mg_cm2=mass_loading,
            measurement_types=list(set(measurement_types)),
            comparison_dimensions=comparison_dimensions,
            raw_query=clean_q,
        )

    def classify_intent(self, query: str, conversation_turn: int = 1) -> ScientificIntentPayload:
        """
        Classify query into one of 18 scientific intents and identify ambiguities.
        Preserves battery-level LMFP questions in scope while rejecting non-LMFP domains.
        """
        entities = self.extract_entities(query)
        lower_q = query.lower().strip()

        # 1. Check for genuine out-of-scope non-LMFP domains
        # NOTE: Pouch cells, electrolyte interactions, or cell-level tests ARE IN SCOPE if they concern LMFP!
        is_lmfp_context = any(k in lower_q for k in ["lmfp", "limnfe", "limn", "olivine", "pnma", "phosphate", "fe/mn", "mn/fe", "sd_no3", "sd_so4"])
        
        strict_non_lmfp_topics = [
            ("sodium-ion", "propylene carbonate"),
            ("vanadium pentoxide",),
            ("pure ncm811 single-crystal without lmfp",),
            ("pure lco pouch cell without lmfp",),
            ("commercial nail penetration safety testing without cathode data",),
        ]
        
        # Out-of-scope / unsupported negative control checks:
        if "sodium" in lower_q or "na-ion" in lower_q or "propylene carbonate" in lower_q:
            return ScientificIntentPayload(
                intent=ScientificIntent.OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE,
                confidence=0.98,
                extracted_entities=entities,
                is_ambiguous=False,
                clarification_question=None,
            )
        if "vanadium pentoxide" in lower_q:
            return ScientificIntentPayload(
                intent=ScientificIntent.OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE,
                confidence=0.98,
                extracted_entities=entities,
                is_ambiguous=False,
            )
        if "nail penetration" in lower_q or "nail test" in lower_q:
            return ScientificIntentPayload(
                intent=ScientificIntent.OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE,
                confidence=0.98,
                extracted_entities=entities,
                is_ambiguous=False,
            )
        if "peo" in lower_q or "solid polymer" in lower_q:
            return ScientificIntentPayload(
                intent=ScientificIntent.OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE,
                confidence=0.98,
                extracted_entities=entities,
                is_ambiguous=False,
            )
        if ("pure lco" in lower_q or "pure ncm811" in lower_q) and not is_lmfp_context:
            return ScientificIntentPayload(
                intent=ScientificIntent.OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE,
                confidence=0.95,
                extracted_entities=entities,
                is_ambiguous=False,
            )

        # 2. Check for follow-up conversational intent
        has_pronoun = bool(re.search(r"\b(it|its|their|they|both|this|these|those|that|the same|former|latter)\b", lower_q))
        is_elliptical = lower_q.startswith(("what about", "how about", "and at", "and the", "and for", "how does that"))
        if conversation_turn > 1 and (has_pronoun or is_elliptical):
            is_ambig = False
            ambig_reason = None
            clarif_q = None
            cand_referents = []

            # If user asks singular "it" / "its" but prior context had multiple referents
            if re.search(r"\b(it|its|that one)\b", lower_q) and len(entities.dopants) == 0 and len(entities.sample_labels) == 0:
                is_ambig = True
                ambig_reason = "Singular pronoun 'it' used without explicit antecedent in current turn."

            return ScientificIntentPayload(
                intent=ScientificIntent.FOLLOW_UP_QUESTION,
                confidence=0.92,
                extracted_entities=entities,
                is_ambiguous=is_ambig,
                ambiguity_reason=ambig_reason,
                requires_clarification=is_ambig,
                clarification_question=clarif_q,
                candidate_referents=cand_referents,
            )

        # 3. Check for Cross-Paper Comparison
        if len(entities.paper_ids) >= 2 or ("p1" in lower_q and ("ref 79" in lower_q or "ref79" in lower_q or "reference [79]" in lower_q or "srep26686" in lower_q)):
            return ScientificIntentPayload(
                intent=ScientificIntent.CROSS_PAPER_COMPARISON,
                confidence=0.95,
                extracted_entities=entities,
                comparison_dimensions=entities.comparison_dimensions or ["papers"],
            )

        # 4. Check for Sample Comparison (explicit physical samples e.g. SD_NO3 vs SD_SO4, Ref29 vs Ref79)
        if len(entities.sample_labels) >= 2 or ("sd_no3" in lower_q and "sd_so4" in lower_q) or ("ref29" in lower_q and "ref79" in lower_q):
            return ScientificIntentPayload(
                intent=ScientificIntent.SAMPLE_COMPARISON,
                confidence=0.96,
                extracted_entities=entities,
                comparison_dimensions=entities.comparison_dimensions or ["samples"],
            )

        # 5. Check for Precursor Comparison
        if ("precursor" in lower_q or "salt" in lower_q) and (
            len(entities.precursors) >= 2 or "conflict" in lower_q or "vs" in lower_q or "compare" in lower_q
        ):
            return ScientificIntentPayload(
                intent=ScientificIntent.PRECURSOR_COMPARISON,
                confidence=0.94,
                extracted_entities=entities,
                comparison_dimensions=["precursors"],
            )

        # 6. Check for Synthesis Comparison
        if ("synthesis" in lower_q or "route" in lower_q or "calcination" in lower_q or "method" in lower_q) and (
            len(entities.synthesis_methods) >= 2 or ("solvothermal" in lower_q and "solid-state" in lower_q) or "compare" in lower_q
        ):
            return ScientificIntentPayload(
                intent=ScientificIntent.SYNTHESIS_COMPARISON,
                confidence=0.94,
                extracted_entities=entities,
                comparison_dimensions=["synthesis_methods"],
            )

        # Check for General Literature Search (must use word boundary to avoid matching 'research')
        if re.search(r"\b(find|search|show papers|what papers|who reported|list papers)\b", lower_q):
            return ScientificIntentPayload(
                intent=ScientificIntent.LITERATURE_SEARCH,
                confidence=0.92,
                extracted_entities=entities,
            )

        # 7. Check for Dopant Analysis (Single or Multi-Dopant)
        if len(entities.dopants) >= 1 or "dop" in lower_q:
            # Check if multi-dopant comparison
            if len(entities.dopants) >= 2 or ("compare" in lower_q and "dop" in lower_q):
                return ScientificIntentPayload(
                    intent=ScientificIntent.DOPANT_ANALYSIS,
                    confidence=0.95,
                    extracted_entities=entities,
                    comparison_dimensions=["dopants"],
                )
            return ScientificIntentPayload(
                intent=ScientificIntent.DOPANT_ANALYSIS,
                confidence=0.93,
                extracted_entities=entities,
            )

        # 8. Check for Composite Modification Analysis (rGO, CNT, Carbon Coating)
        if len(entities.modifications) >= 1 or "rgo" in lower_q or "carbon" in lower_q or "cnt" in lower_q:
            if "unmodified" in lower_q or "pristine" in lower_q or "plain" in lower_q or "compare" in lower_q:
                return ScientificIntentPayload(
                    intent=ScientificIntent.COMPOSITE_MODIFICATION_ANALYSIS,
                    confidence=0.94,
                    extracted_entities=entities,
                    comparison_dimensions=["modifications"],
                )
            return ScientificIntentPayload(
                intent=ScientificIntent.COMPOSITE_MODIFICATION_ANALYSIS,
                confidence=0.91,
                extracted_entities=entities,
            )

        # 9. Check for Research Gap Analysis
        if any(k in lower_q for k in ["research gap", "unaddressed", "gap", "future study", "limitation in literature", "55°c", "high temperature cycling"]):
            return ScientificIntentPayload(
                intent=ScientificIntent.RESEARCH_GAP_ANALYSIS,
                confidence=0.92,
                extracted_entities=entities,
            )

        # 10. Check for Mechanism Explanation (Jahn-Teller, polarons, Mn dissolution, SEI, first cycle loss)
        if any(k in lower_q for k in ["mechanism", "why", "jahn-teller", "dissolution", "disproportionation", "electronic conductivity", "1d diffusion", "b-axis", "polaron"]):
            return ScientificIntentPayload(
                intent=ScientificIntent.MECHANISM_EXPLANATION,
                confidence=0.92,
                extracted_entities=entities,
            )

        # 11. Check for Cycling Stability Analysis
        if any(k in lower_q for k in ["cycling", "retention", "cycles", "1000 cycles", "500 cycles", "cycle life", "fade"]):
            return ScientificIntentPayload(
                intent=ScientificIntent.CYCLING_STABILITY_ANALYSIS,
                confidence=0.93,
                extracted_entities=entities,
                target_measurements=["capacity_retention"],
            )

        # 10. Check for Sample Property Lookup (Single Sample)
        if (len(entities.sample_labels) == 1 or len(entities.sample_ids) == 1) and not (
            "rate capability" in lower_q or len(entities.c_rates) >= 2 or "compare" in lower_q or "vs" in lower_q
        ):
            return ScientificIntentPayload(
                intent=ScientificIntent.SAMPLE_PROPERTY_LOOKUP,
                confidence=0.95,
                extracted_entities=entities,
            )

        # 11. Check for Rate Capability Analysis
        if len(entities.c_rates) >= 1 or any(k in lower_q for k in ["rate capability", "high rate", "high-rate", "at 5c", "at 10c", "at 20c", "c-rate"]):
            return ScientificIntentPayload(
                intent=ScientificIntent.RATE_CAPABILITY_ANALYSIS,
                confidence=0.94,
                extracted_entities=entities,
                target_measurements=["discharge_capacity", "rate_capability"],
            )

        # 14. Check for Characterization Analysis (XRD, EIS, Morphology, Space group)
        if any(k in lower_q for k in ["xrd", "pnma", "space group", "crystal structure", "eis", "rct", "morphology", "impurity phase", "fe2o3", "fe3+"]):
            return ScientificIntentPayload(
                intent=ScientificIntent.CHARACTERIZATION_ANALYSIS,
                confidence=0.92,
                extracted_entities=entities,
                target_measurements=["crystallography", "eis_rct"],
            )

        # 15. Check for Composition Comparison (Mn/Fe ratios e.g. Mn0.8Fe0.2 vs Mn0.5Fe0.5)
        if ("mn0.8" in lower_q and "mn0.5" in lower_q) or ("manganese content" in lower_q and "trade" in lower_q) or ("stoichiometry" in lower_q and "trade" in lower_q):
            return ScientificIntentPayload(
                intent=ScientificIntent.COMPOSITION_COMPARISON,
                confidence=0.94,
                extracted_entities=entities,
                comparison_dimensions=["stoichiometry"],
            )

        # 15. Check for Sample Property Lookup (Single Sample)
        if len(entities.sample_labels) == 1 or len(entities.sample_ids) == 1:
            return ScientificIntentPayload(
                intent=ScientificIntent.SAMPLE_PROPERTY_LOOKUP,
                confidence=0.91,
                extracted_entities=entities,
            )

        # 16. Check for Experimental Condition Filter
        if entities.voltage_window is not None or entities.temperature_c is not None or entities.mass_loading_mg_cm2 is not None:
            return ScientificIntentPayload(
                intent=ScientificIntent.EXPERIMENTAL_CONDITION_FILTER,
                confidence=0.90,
                extracted_entities=entities,
            )

        # 17. Default fallback: Electrochemical Performance Analysis
        return ScientificIntentPayload(
            intent=ScientificIntent.ELECTROCHEMICAL_PERFORMANCE_ANALYSIS,
            confidence=0.80,
            extracted_entities=entities,
            target_measurements=entities.measurement_types or ["discharge_capacity"],
        )
