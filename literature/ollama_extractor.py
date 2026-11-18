
"""Extract LMFP literature data using the local Ollama model."""

import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:4b"


def ask_ollama(prompt: str, num_predict: int = 1800) -> str:
    """Send a prompt to Ollama and return the model response."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "format": "json",
                "think": False,
                "stream": False,
                "options": {
                    "num_predict": num_predict,
                    "temperature": 0,
                },
            },
            timeout=(10, 600),
        )
        response.raise_for_status()
        return response.json()["response"].strip()

    except requests.RequestException as exc:
        raise RuntimeError(
            "Could not connect to Ollama. Check that Ollama is running."
        ) from exc


def _parse_json(response: str, page_number: int) -> dict:
    """Parse and validate the top-level JSON object."""
    try:
        data = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Qwen returned invalid JSON for page {page_number}. "
            "Try extracting a smaller section."
        ) from exc

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object from Qwen.")

    return data


def extract_lmfp_table(page_text: str, page_number: int) -> dict:
    """Extract structured records from a literature table."""

    lower_text = page_text.lower()

    # Start near the table title/header when possible.
    markers = [
        "methods of element doping of lmfp",
        "table 2",
    ]

    start = -1
    for marker in markers:
        position = lower_text.find(marker)
        if position >= 0:
            start = position
            break

    table_text = page_text[start:] if start >= 0 else page_text

    # Avoid sending an unnecessarily large page to the local model.
    table_text = table_text[:12000]

    prompt = f"""
You extract scientific literature records from a battery-materials table.

The supplied text comes from a PDF page. It may contain flattened table
cells, line breaks, and surrounding paragraphs.

Identify the table about methods of element doping of LMFP.
Extract each distinct data row. Do not merge different rows.

The table columns are:
year, composition, synthesis_method, doping_agent, doping_element,
rate_capability, capacity_retention, active_mass_loading,
voltage_window, reference.

Return valid JSON with exactly these top-level fields:
{{
  "table_rows": [
    {{
      "year": null,
      "composition": null,
      "synthesis_method": null,
      "doping_agent": null,
      "doping_element": null,
      "rate_capability": null,
      "capacity_retention": null,
      "active_mass_loading": null,
      "voltage_window": null,
      "reference": null,
      "evidence_quote": "",
      "page": {page_number}
    }}
  ]
}}

Rules:
- Extract only rows actually present in the supplied text.
- Preserve reported numbers, chemical formulas, units, and references.
- Do not infer missing values. Use null for missing fields.
- Preserve multiple rate-capability and retention measurements.
- Keep each row's own reference, such as [74] or [63].
- evidence_quote must be a short verbatim excerpt supporting that row.
- The page value must always be {page_number}.
- Do not include column headings as records.
- If no data rows can be identified, return an empty table_rows array.
- Return JSON only. Do not explain your answer.

PDF TEXT:
{table_text}
"""

    data = _parse_json(
        ask_ollama(prompt, num_predict=3000),
        page_number,
    )

    rows = data.get("table_rows")

    if not isinstance(rows, list):
        raise ValueError(
            f"Qwen did not return a table_rows list for page {page_number}."
        )

    # Reject malformed records and attach trusted page provenance.
    validated_rows = []

    required_fields = [
        "year",
        "composition",
        "synthesis_method",
        "doping_agent",
        "doping_element",
        "rate_capability",
        "capacity_retention",
        "active_mass_loading",
        "voltage_window",
        "reference",
        "evidence_quote",
    ]

    for row in rows:
        if not isinstance(row, dict):
            continue

        record = {
            field: row.get(field)
            for field in required_fields
        }

        # Keep the actual PDF page number rather than trusting the model.
        record["page"] = page_number

        # Do not accept empty records or records without supporting evidence.
        if not record["composition"] and not record["reference"]:
            continue

        if not isinstance(record["evidence_quote"], str):
            record["evidence_quote"] = ""

        validated_rows.append(record)

    data["table_rows"] = validated_rows
    return data


import re



def parse_lmfp_doping_table(page_text: str, page_number: int) -> dict:
    """Parse the LMFP doping table while preserving wrapped cell values."""
    import re

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in page_text.replace("\xa0", " ").splitlines()
    ]
    lines = [line for line in lines if line]

    start = next(
        (
            i for i, line in enumerate(lines)
            if "methods of element doping of lmfp" in line.lower()
        ),
        None,
    )
    if start is None:
        return {"table_rows": []}

    lines = lines[start + 1:]

    row_starts = [
        i for i in range(len(lines) - 1)
        if re.fullmatch(r"20\d{2}", lines[i])
        and re.match(r"LiMn[\d.]+Fe[\d.]+PO4", lines[i + 1])
    ]

    records = []

    for idx, begin in enumerate(row_starts):
        end = row_starts[idx + 1] if idx + 1 < len(row_starts) else len(lines)
        row = lines[begin:end]

        # Exclude trailing footnotes and journal footer text.
        ref_pos = next(
            (i for i in range(len(row) - 1, -1, -1)
             if re.fullmatch(r"\[\d+\]", row[i])),
            None,
        )
        if ref_pos is None:
            continue

        cells = row[:ref_pos]
        reference = row[ref_pos]

        if len(cells) < 8:
            continue

        year, composition = cells[0], cells[1]
        body = cells[2:]

        # Locate the element column using known values from this table.
        known_elements = {
            "B", "B/P", "Y", "Ni", "Ca", "N", "N/S",
            "Nb/Mg", "Ni/Mg", "V", "Zn", "Cr", "F", "Na", "F/In",
        }
        element_pos = next(
            (i for i, value in enumerate(body) if value in known_elements),
            None,
        )
        if element_pos is None:
            continue

        # The last two cells are voltage window and mass loading.
        voltage_pos = next(
            (
                i for i in range(len(body) - 1, element_pos, -1)
                if re.search(
                    r"\d+(?:\.\d+)?\s*[\u2013\u2212\-\ufffd?~]\s*\d+(?:\.\d+)?",
                    body[i],
                )
            ),
            None,
        )
        if voltage_pos is None or voltage_pos < 2:
            continue

        voltage = body[voltage_pos]
        loading = body[voltage_pos - 1]

        # The element is followed by rate capability, then retention.
        data_body = body[element_pos + 1:voltage_pos - 1]
        rate_pos = next(
            (
                i for i, value in enumerate(data_body)
                if re.search(r"\d+(?:\.\d+)?\s*\(\s*\d+(?:\.\d+)?\s*C\s*\)", value)
            ),
            None,
        )
        if rate_pos is None:
            continue

        retention_pos = next(
            (
                i for i in range(rate_pos + 1, len(data_body))
                if re.search(r"\d+(?:\.\d+)?\s*%", data_body[i])
            ),
            None,
        )
        if retention_pos is None:
            continue

        rate = " ".join(data_body[rate_pos:retention_pos])
        retention = " ".join(data_body[retention_pos:])

        # Remaining cells before the element are synthesis method and agent.
        # Use the formula/reagent boundary heuristics to separate them.
        prefix = body[:element_pos]
        reagent_start = next(
            (
                i for i, value in enumerate(prefix)
                if re.match(
                    r"^(?:H3BO3|Y2\(|NiSO4|C12H22|Melamine|CTAB|CBMM|"
                    r"MgC2O4|VCl3|ZnSO4|Cr2O3|PVDF|NaC6|NH4F|"
                    r"triphenylphosphine|MgSO4)",
                    value,
                    re.IGNORECASE,
                )
            ),
            None,
        )

        if reagent_start is None:
            # Keep the unclassified values visible for human review.
            synthesis = " ".join(prefix)
            agent = None
        else:
            synthesis = " ".join(prefix[:reagent_start])
            agent = " ".join(prefix[reagent_start:])

        records.append({
            "year": year,
            "composition": composition,
            "synthesis_method": synthesis or None,
            "doping_agent": agent,
            "doping_element": body[element_pos],
            "rate_capability": rate,
            "capacity_retention": retention,
            "active_mass_loading": loading,
            "voltage_window": voltage,
            "reference": reference,
            "evidence_quote": " | ".join(row),
            "page": page_number,
        })

    return {"table_rows": records}



def extract_lmfp_data(page_text: str, page_number: int) -> dict:
    """Extract LMFP table data or general research information."""

    lower_text = page_text.lower()

    is_doping_table = (
        "methods of element doping of lmfp" in lower_text
        or (
            "doping element" in lower_text
            and "capacity retention" in lower_text
            and "voltage window" in lower_text
        )
    )

    if is_doping_table:
        result = parse_lmfp_doping_table(page_text, page_number)

        if result["table_rows"]:
            return result

        # Fall back to Qwen if deterministic parsing finds no rows.
        return extract_lmfp_table(page_text, page_number)

    prompt = f"""
Extract scientific information explicitly reported in this research text.

Return valid JSON with exactly these fields:
{{
  "title": null,
  "composition": null,
  "dopants": [],
  "synthesis_conditions": [],
  "electrochemical_results": [],
  "xrd_phases": [],
  "other_findings": [],
  "evidence": []
}}

Each synthesis_conditions item:
{{"parameter": "", "value": "", "unit": ""}}

Each electrochemical_results item:
{{"metric": "", "value": "", "unit": "", "test_conditions": ""}}

Each evidence item:
{{"field": "", "value": "", "quote": "", "page": {page_number}}}

Rules:
- Never infer an exact composition from the acronym LMFP.
- Missing information must be null or an empty array.
- Do not invent values, units, experimental results, or conditions.
- Provide a supporting quote for each extracted fact.
- Use page number {page_number} for evidence from this text.
- Return JSON only.

RESEARCH TEXT:
{page_text[:10000]}
"""

    return _parse_json(
        ask_ollama(prompt),
        page_number,
    )


def extract_lmfp_document(pages: list[dict]) -> dict:
    """Extract LMFP information from every page of a PDF."""

    all_table_rows = []
    all_page_results = []
    errors = []

    for page in pages:
        page_number = page["page"]
        page_text = page["text"]

        if not page_text.strip():
            continue

        try:
            result = extract_lmfp_data(page_text, page_number)

            if isinstance(result.get("table_rows"), list):
                all_table_rows.extend(result["table_rows"])
            else:
                all_page_results.append({
                    "page": page_number,
                    "data": result,
                })

        except (ValueError, RuntimeError) as exc:
            errors.append({
                "page": page_number,
                "error": str(exc),
            })

    return {
        "source_pages": len(pages),
        "table_rows": all_table_rows,
        "page_results": all_page_results,
        "errors": errors,
    }
