"""
Literature Matching Module for HE-LMFP Designer.

Provides loading, parsing, deterministic matching, and evidence extraction
for literature reference records.
"""

from .loader import load_literature_database, LiteratureSampleRecord
from .parser import parse_composition, ParsedComposition
from .matcher import match_composition, exact_match, MatchResult, MatchStatus
from .evidence import generate_evidence_summary, format_evidence_report

__all__ = [
    "load_literature_database",
    "LiteratureSampleRecord",
    "parse_composition",
    "ParsedComposition",
    "match_composition",
    "exact_match",
    "MatchResult",
    "MatchStatus",
    "generate_evidence_summary",
    "format_evidence_report",
]
