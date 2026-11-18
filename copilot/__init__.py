"""LMFP Research Copilot module for HE-LMFP-Designer."""

from copilot.engine import LMFPResearchCopilot, get_research_copilot, reload_copilot_index
from copilot.evidence_organizer import EvidenceOrganizer
from copilot.grounding import DynamicScientificSynthesizer
from copilot.index import ScientificPassageIndex, get_passage_index, reload_passage_index
from copilot.models import (
    ConditionParityResult,
    CopilotCitation,
    CopilotResponseData,
    EvidencePassage,
    MeasurementRecord,
    RetrievalMatch,
    StructuredSampleProfile,
)
from copilot.retriever import HybridRetriever

__all__ = [
    "LMFPResearchCopilot",
    "get_research_copilot",
    "reload_copilot_index",
    "EvidenceOrganizer",
    "DynamicScientificSynthesizer",
    "ScientificPassageIndex",
    "get_passage_index",
    "reload_passage_index",
    "HybridRetriever",
    "CopilotCitation",
    "CopilotResponseData",
    "EvidencePassage",
    "MeasurementRecord",
    "RetrievalMatch",
    "StructuredSampleProfile",
    "ConditionParityResult",
]
