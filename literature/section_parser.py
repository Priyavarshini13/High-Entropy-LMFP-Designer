"""
Publisher-Independent Document Structure and Section Zoning Engine for Scientific Literature.

Classifies peer-reviewed research papers into standard structural zones:
- ABSTRACT
- INTRODUCTION (Introduction / Background / Literature Review)
- EXPERIMENTAL (Materials & Methods / Synthesis / Electrochemical Testing)
- RESULTS_DISCUSSION (Results and Discussion / Characterization / Performance)
- TABLE (Tables & Table Captions)
- FIGURE_CAPTION (Figure Captions & Schemes)
- CONCLUSION (Conclusions / Summary / Outlook)
- REFERENCES (Bibliography / Literature Cited)
- ACKNOWLEDGEMENTS (Funding / Competing Interests / Contributions)
- CORRIGENDUM (Corrections / Errata)
- UNKNOWN (Running headers, front-matter metadata, unclassified blocks)

Distinguishes primary experimental evidence from background literature citations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re


class SectionType(str, Enum):
    """Semantic section categories in scientific literature."""
    ABSTRACT = "ABSTRACT"
    INTRODUCTION = "INTRODUCTION"
    EXPERIMENTAL = "EXPERIMENTAL"
    RESULTS_DISCUSSION = "RESULTS_DISCUSSION"
    TABLE = "TABLE"
    FIGURE_CAPTION = "FIGURE_CAPTION"
    CONCLUSION = "CONCLUSION"
    REFERENCES = "REFERENCES"
    ACKNOWLEDGEMENTS = "ACKNOWLEDGEMENTS"
    CORRIGENDUM = "CORRIGENDUM"
    UNKNOWN = "UNKNOWN"


def is_experimental_section(sec_type: SectionType) -> bool:
    """Return True if section contains primary experimental methods or results."""
    return sec_type in {
        SectionType.EXPERIMENTAL,
        SectionType.RESULTS_DISCUSSION,
        SectionType.TABLE,
        SectionType.FIGURE_CAPTION,
    }


def is_background_section(sec_type: SectionType) -> bool:
    """Return True if section discusses prior literature or broad context."""
    return sec_type in {
        SectionType.ABSTRACT,
        SectionType.INTRODUCTION,
        SectionType.CONCLUSION,
    }


def is_non_scientific_section(sec_type: SectionType) -> bool:
    """Return True if section must never generate experimental sample records."""
    return sec_type in {
        SectionType.REFERENCES,
        SectionType.ACKNOWLEDGEMENTS,
        SectionType.CORRIGENDUM,
        SectionType.UNKNOWN,
    }


@dataclass
class SectionBlock:
    """A segmented, typed block of text with provenance and evidence role."""
    block_id: str
    section_type: SectionType
    section_label: str
    page_number: int
    text: str
    is_experimental: bool = False
    is_background: bool = False
    table_id: Optional[str] = None
    figure_id: Optional[str] = None
    confidence: float = 1.0
    char_offset_start: int = 0
    char_offset_end: int = 0


@dataclass
class DocumentStructure:
    """Document-level structural representation across all pages."""
    source_pdf: str
    total_pages: int
    blocks: List[SectionBlock] = field(default_factory=list)
    section_page_map: Dict[str, List[int]] = field(default_factory=dict)
    detected_sections: List[str] = field(default_factory=list)

    def get_blocks_by_type(self, section_type: SectionType) -> List[SectionBlock]:
        """Return all blocks of a given section type."""
        return [b for b in self.blocks if b.section_type == section_type]

    def get_experimental_blocks(self) -> List[SectionBlock]:
        """Return blocks containing primary experimental evidence."""
        return [b for b in self.blocks if b.is_experimental]

    def get_background_blocks(self) -> List[SectionBlock]:
        """Return blocks containing background literature or summary evidence."""
        return [b for b in self.blocks if b.is_background]

    def get_excluded_blocks(self) -> List[SectionBlock]:
        """Return blocks strictly excluded from sample creation (e.g. references)."""
        return [b for b in self.blocks if is_non_scientific_section(b.section_type)]


# ---------------------------------------------------------------------------
# Section Heading Regular Expressions (Publisher-Independent)
# ---------------------------------------------------------------------------

HEADING_PATTERNS: List[Tuple[SectionType, re.Pattern]] = [
    (
        SectionType.CORRIGENDUM,
        re.compile(
            r"^\s*(?:corrigendum(?:\s+to)?|erratum|correction\s+to:?|author\s+correction)\b",
            re.IGNORECASE,
        ),
    ),
    (
        SectionType.REFERENCES,
        re.compile(
            r"^\s*(?:(?:\d+|[IVXLCDM]+)[\.\:\-\s]+)?(?:references?|bibliography|literature\s+cited)\s*$",
            re.IGNORECASE,
        ),
    ),
    (
        SectionType.ACKNOWLEDGEMENTS,
        re.compile(
            r"^\s*(?:(?:\d+|[IVXLCDM]+)[\.\:\-\s]+)?(?:acknowledgements?|acknowledgments?|funding(?:\s+information)?|author\s+contributions?|declaration\s+of\s+competing\s+interest|competing\s+interests?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        SectionType.CONCLUSION,
        re.compile(
            r"^\s*(?:(?:\d+|[IVXLCDM]+)[\.\:\-\s]+)?(?:conclusions?(?:\s*(?:and|&)\s*(?:outlook|remarks))?|summary\s*(?:and|&)\s*(?:outlook|concluding\s+remarks)|summary|concluding\s+remarks)\s*$",
            re.IGNORECASE,
        ),
    ),
    (
        SectionType.RESULTS_DISCUSSION,
        re.compile(
            r"^\s*(?:(?:\d+|[IVXLCDM]+)[\.\:\-\s]+)?(?:results?\s*(?:and|&)\s*discussions?|results?\s*(?:and|&)\s*analysis|results?|discussions?|electrochemical\s+performance|structure\s*(?:and|&)\s*morphology)\s*(?:[:\.\-]|\s*$)",
            re.IGNORECASE,
        ),
    ),
    (
        SectionType.EXPERIMENTAL,
        re.compile(
            r"^\s*(?:(?:\d+|[IVXLCDM]+)[\.\:\-\s]+)?(?:experimental(?:\s+(?:section|methods?|procedures?|part|details?))?|materials?\s*(?:and|&)\s*methods?|methodology|synthesis\s*(?:and|&)\s*characterization|preparation\s+of\b|electrochemical\s+measurements?|sample\s+preparation)\b",
            re.IGNORECASE,
        ),
    ),
    (
        SectionType.INTRODUCTION,
        re.compile(
            r"^\s*(?:(?:\d+|[IVXLCDM]+)[\.\:\-\s]+)?(?:introduction(?:\s*(?:and|&)\s*background)?|background(?:\s*(?:and|&)\s*(?:literature\s+review|prior\s+work|context))?|literature\s+review)\s*(?:[:\.\-]|\s*$)",
            re.IGNORECASE,
        ),
    ),
    (
        SectionType.ABSTRACT,
        re.compile(
            r"^\s*(?:abstract|graphical\s+abstract)\s*(?:[:\.\-]|\s*$)",
            re.IGNORECASE,
        ),
    ),
]

TABLE_HEADING_PATTERN = re.compile(
    r"^\s*(Table\s+(\d+|[IVXLCDM]+))[\.:\s\-]+(.*)",
    re.IGNORECASE,
)

FIGURE_CAPTION_PATTERN = re.compile(
    r"^\s*((?:Fig(?:\.|ure)?|Scheme)\s+(\d+|[IVXLCDM]+))[\.:\s\-]+(.*)",
    re.IGNORECASE,
)

RUNNING_HEADER_FOOTER_PATTERNS = [
    re.compile(r"^\s*(?:page\s+\d+(?:\s+of\s+\d+)?|\d+\s*/\s*\d+)\s*$", re.IGNORECASE),
    re.compile(r"^\s*https?://(?:dx\.)?doi\.org/\S+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d{4}\s+elsevier\s+b\.v\.\s+all\s+rights\s+reserved\.\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:journal\s+of\s+|electrochimica\s+acta|adv(?:anced)?\.\s+energy\s+mater|nat(?:ure)?\.\s+energy)\b.*?\d{4}.*?$", re.IGNORECASE),
]


def is_running_header_or_footer(line: str, page_number: int, total_pages: int) -> bool:
    """Detect running headers, footers, pagination, and copyright notices."""
    clean = line.strip()
    if len(clean) < 3 or len(clean) > 160:
        return False
    for pat in RUNNING_HEADER_FOOTER_PATTERNS:
        if pat.match(clean):
            return True
    return False


def classify_heading(line: str) -> Tuple[Optional[SectionType], Optional[str]]:
    """Determine if a single line or title represents a major section header."""
    clean = line.strip()
    if len(clean) > 90 or len(clean) < 3:
        return None, None

    for sec_type, pat in HEADING_PATTERNS:
        if pat.search(clean):
            return sec_type, clean
    return None, None


def classify_table_or_figure(line: str) -> Tuple[Optional[SectionType], Optional[str], Optional[str]]:
    """Detect table headers or figure captions."""
    clean = line.strip()
    t_match = TABLE_HEADING_PATTERN.match(clean)
    if t_match:
        table_id = t_match.group(1).title()
        return SectionType.TABLE, clean, table_id

    f_match = FIGURE_CAPTION_PATTERN.match(clean)
    if f_match:
        fig_id = f_match.group(1).title()
        return SectionType.FIGURE_CAPTION, clean, fig_id

    return None, None, None


def _is_structural_boundary(line: str) -> bool:
    """Check if a line marks a boundary (heading, table, or figure) that begins a new block."""
    clean = line.strip()
    if not clean:
        return False
    # Check table / figure
    if TABLE_HEADING_PATTERN.match(clean) or FIGURE_CAPTION_PATTERN.match(clean):
        return True
    # Check section heading
    sec, _ = classify_heading(clean)
    if sec is not None:
        return True
    return False


def _split_into_structural_paragraphs(page_text: str) -> List[str]:
    """
    Split page text into distinct paragraph chunks, ensuring headings,
    tables, and figure captions start on their own independent chunk.
    """
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return []

    chunks: List[str] = []
    current_chunk: List[str] = []

    for line in lines:
        if _is_structural_boundary(line) and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
        else:
            current_chunk.append(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def segment_page_text(
    page_text: str,
    page_number: int,
    current_section: SectionType = SectionType.UNKNOWN,
    current_label: str = "Front Matter",
) -> Tuple[List[SectionBlock], SectionType, str]:
    """
    Segment a single page into logical blocks tagged with section provenance.

    Returns:
    - List of SectionBlocks for this page.
    - Resulting active section type at end of page.
    - Resulting active section label at end of page.
    """
    blocks: List[SectionBlock] = []
    raw_paragraphs = _split_into_structural_paragraphs(page_text)

    block_idx = 0
    char_offset = 0

    for para in raw_paragraphs:
        unwrapped_para = re.sub(r"\s*\n\s*", " ", para).strip()
        if not unwrapped_para:
            continue

        lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
        first_line = lines[0] if lines else unwrapped_para

        # 1. Check for Running Header / Footer
        if len(lines) == 1 and is_running_header_or_footer(first_line, page_number, 0):
            block = SectionBlock(
                block_id=f"p{page_number}_b{block_idx}",
                section_type=SectionType.UNKNOWN,
                section_label="Running Header/Footer",
                page_number=page_number,
                text=unwrapped_para,
                is_experimental=False,
                is_background=False,
                confidence=0.9,
                char_offset_start=char_offset,
                char_offset_end=char_offset + len(unwrapped_para),
            )
            blocks.append(block)
            block_idx += 1
            char_offset += len(unwrapped_para) + 1
            continue

        # 2. Check for Table or Figure Caption
        tf_type, tf_label, tf_id = classify_table_or_figure(first_line)
        if tf_type is not None:
            table_id = tf_id if tf_type == SectionType.TABLE else None
            figure_id = tf_id if tf_type == SectionType.FIGURE_CAPTION else None
            block = SectionBlock(
                block_id=f"p{page_number}_b{block_idx}",
                section_type=tf_type,
                section_label=tf_label or tf_id or "Table/Figure",
                page_number=page_number,
                text=unwrapped_para,
                is_experimental=True,
                is_background=False,
                table_id=table_id,
                figure_id=figure_id,
                confidence=0.95,
                char_offset_start=char_offset,
                char_offset_end=char_offset + len(unwrapped_para),
            )
            blocks.append(block)
            block_idx += 1
            char_offset += len(unwrapped_para) + 1
            continue

        # 3. Check for Section Heading in first line
        new_sec, new_lbl = classify_heading(first_line)
        if new_sec is not None:
            current_section = new_sec
            current_label = new_lbl or current_section.value

            # If paragraph is JUST the heading, register heading block
            if len(lines) == 1 or len(unwrapped_para) == len(first_line):
                block = SectionBlock(
                    block_id=f"p{page_number}_b{block_idx}",
                    section_type=current_section,
                    section_label=current_label,
                    page_number=page_number,
                    text=unwrapped_para,
                    is_experimental=is_experimental_section(current_section),
                    is_background=is_background_section(current_section),
                    confidence=1.0,
                    char_offset_start=char_offset,
                    char_offset_end=char_offset + len(unwrapped_para),
                )
                blocks.append(block)
                block_idx += 1
                char_offset += len(unwrapped_para) + 1
                continue
            else:
                body_text = unwrapped_para[len(first_line):].strip()
                unwrapped_para = body_text if body_text else unwrapped_para

        # 4. Standard body block inheriting active section
        block = SectionBlock(
            block_id=f"p{page_number}_b{block_idx}",
            section_type=current_section,
            section_label=current_label,
            page_number=page_number,
            text=unwrapped_para,
            is_experimental=is_experimental_section(current_section),
            is_background=is_background_section(current_section),
            confidence=0.9 if current_section != SectionType.UNKNOWN else 0.5,
            char_offset_start=char_offset,
            char_offset_end=char_offset + len(unwrapped_para),
        )
        blocks.append(block)
        block_idx += 1
        char_offset += len(unwrapped_para) + 1

    return blocks, current_section, current_label


def segment_document_pages(
    pages: List[Dict[str, Any]],
    source_pdf: str = "",
) -> DocumentStructure:
    """
    Segment all pages of a scientific publication into structural zones.

    Maintains section state across pages (e.g. experimental methods spanning p. 2 to p. 3).
    """
    all_blocks: List[SectionBlock] = []
    section_page_map: Dict[str, List[int]] = {}
    detected_sections_set = set()

    current_sec = SectionType.UNKNOWN
    current_lbl = "Front Matter"

    for p in pages:
        page_num = p.get("page", 1)
        page_text = p.get("text", "")

        page_blocks, current_sec, current_lbl = segment_page_text(
            page_text=page_text,
            page_number=page_num,
            current_section=current_sec,
            current_label=current_lbl,
        )

        for b in page_blocks:
            all_blocks.append(b)
            sec_name = b.section_type.value
            detected_sections_set.add(sec_name)
            if sec_name not in section_page_map:
                section_page_map[sec_name] = []
            if page_num not in section_page_map[sec_name]:
                section_page_map[sec_name].append(page_num)

    return DocumentStructure(
        source_pdf=source_pdf,
        total_pages=len(pages),
        blocks=all_blocks,
        section_page_map=section_page_map,
        detected_sections=sorted(list(detected_sections_set)),
    )
