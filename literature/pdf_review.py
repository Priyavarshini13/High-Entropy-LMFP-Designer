"""PDF literature upload and extraction review interface."""

import streamlit as st

from literature.pdf_extractor import extract_pdf_pages
from literature.ollama_extractor import (
    extract_lmfp_data,
    extract_lmfp_document,
)
from literature.review_store import (
    save_extraction,
    update_review,
    list_reviews,
    find_matching_review,
)


def _save_or_update_review(
    record,
    status,
    review_key,
    source_pdf=None,
    state_store=None,
):
    """Create a review once, then update the same review on later actions."""
    if state_store is None:
        state_store = st.session_state

    if source_pdf is None:
        source_pdf = state_store.get(
            "lmfp_pdf_name", "unknown.pdf"
        )

    saved_ids = state_store.setdefault(
        "lmfp_saved_review_ids", {}
    )

    review_id = saved_ids.get(review_key)

    if review_id is not None:
        try:
            update_review(
                review_id=review_id,
                record=record,
                status=status,
            )
            return review_id, False
        except ValueError:
            # If the referenced review was removed, fall through to re-create or re-find.
            review_id = None

    # Check if a matching review already exists for this exact paper and sample.
    matching_id = find_matching_review(
        source_pdf=source_pdf,
        page_number=record.get("page"),
        composition=record.get("composition"),
        reference=record.get("reference"),
    )

    if matching_id is not None:
        update_review(
            review_id=matching_id,
            record=record,
            status=status,
        )
        saved_ids[review_key] = matching_id
        return matching_id, False

    review_id = save_extraction(
        source_pdf=source_pdf,
        record=record,
        status=status,
    )
    saved_ids[review_key] = review_id
    return review_id, True

def render_pdf_review_section():
    st.header("📄 PDF Literature Extraction")
    st.write(
        "Upload a research paper to extract LMFP materials data "
        "using your local Qwen model."
    )

    uploaded_pdf = st.file_uploader(
        "Upload a research paper (PDF)",
        type=["pdf"],
        key="lmfp_pdf_upload",
    )

    if uploaded_pdf is None:
        st.info("Upload a PDF to begin.")
        return

    if st.button("Extract Literature Data", key="extract_lmfp_pdf"):
        try:
            with st.spinner("Reading PDF pages..."):
                pages = extract_pdf_pages(uploaded_pdf.getvalue())

            st.success(f"PDF read successfully: {len(pages)} pages.")

            # Keep the extracted text in the current Streamlit session.
            st.session_state["lmfp_pdf_pages"] = pages
            st.session_state["lmfp_pdf_name"] = uploaded_pdf.name
            st.session_state.pop("lmfp_extraction_results", None)
            st.session_state.pop("lmfp_document_results", None)
            st.session_state["lmfp_saved_review_ids"] = {}

            # Start with pages containing likely experimental information.
            keywords = (
                "capacity",
                "retention",
                "synthesis",
                "discharge",
                "doping",
                "calcination",
                "electrochemical",
            )

            candidate_pages = [
                page
                for page in pages
                if any(
                    keyword in page["text"].lower()
                    for keyword in keywords
                )
            ]

            st.session_state["lmfp_candidate_pages"] = [
                page["page"] for page in candidate_pages
            ]

            st.write(
                f"Found {len(candidate_pages)} pages containing "
                "potentially relevant information."
            )

            st.info(
                "PDF reading is complete. Choose a page below to test "
                "the extraction before processing more pages."
            )

        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))

    pages = st.session_state.get("lmfp_pdf_pages", [])
    
    
    if pages:
        st.divider()
        st.subheader("Full-document extraction")

        st.write(
            f"Ready to process {len(pages)} PDF pages. "
            "This may take several minutes because Qwen runs locally."
        )

        if st.button(
            "Extract Entire PDF",
            key="extract_entire_lmfp_pdf",
        ):
            with st.spinner(
                "Processing all PDF pages. Please wait..."
            ):
                try:
                    st.session_state["lmfp_saved_review_ids"] = {}

                    document_result = extract_lmfp_document(pages)

                    st.session_state["lmfp_document_results"] = (
                        document_result
                    )

                except (ValueError, RuntimeError) as exc:
                    st.error(str(exc))

    document_result = st.session_state.get(
        "lmfp_document_results"
    )

    if document_result:
        st.subheader("Full-document extraction results")

        st.write(
            f"Pages processed: {document_result['source_pages']}"
        )
        st.write(
            f"Table rows extracted: "
            f"{len(document_result['table_rows'])}"
        )
        st.write(
            f"Pages with extraction errors: "
            f"{len(document_result['errors'])}"
        )

        if document_result["table_rows"]:
            st.subheader("Review extracted literature records")

            records = document_result["table_rows"]

            st.caption(
                "Review each record against the original PDF before approval. "
                "Approved records are stored separately from the master CSV."
            )

            for index, original_record in enumerate(records):
                with st.expander(
                    f"Record {index + 1}: "
                    f"{original_record.get('composition', 'Unknown composition')} "
                    f"— Page {original_record.get('page', '?')}",
                    expanded=(index == 0),
                ):
                    record = dict(original_record)

                    editable_fields = [
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
                    ]

                    for field in editable_fields:
                        value = record.get(field)
                        if value is None:
                            value = ""

                        record[field] = st.text_input(
                            field.replace("_", " ").title(),
                            value=str(value),
                            key=f"review_{index}_{field}",
                        )

                    record["evidence_quote"] = st.text_area(
                        "Evidence quote",
                        value=str(record.get("evidence_quote") or ""),
                        key=f"review_{index}_evidence",
                    )

                    st.markdown("---")
                    st.markdown("##### 🔬 Reviewer Verification & Identity Disambiguation")
                    st.caption(
                        "Verify scientific paper identity, sample designation, rate capacities, and cycling conditions. "
                        "Records without verified Paper_ID and Sample_ID will remain blocked from export."
                    )

                    c_p1, c_p2 = st.columns(2)
                    with c_p1:
                        record["verified_paper_id"] = st.text_input(
                            "Verified Paper ID (e.g. P1)",
                            value=str(record.get("verified_paper_id") or ""),
                            key=f"review_{index}_v_paper_id",
                            help="Identifier matching the paper in the master dataset."
                        )
                        record["verified_doi"] = st.text_input(
                            "DOI (e.g. 10.1039/d2ra04427g)",
                            value=str(record.get("verified_doi") or ""),
                            key=f"review_{index}_v_doi",
                        )
                    with c_p2:
                        record["verified_sample_id"] = st.text_input(
                            "Verified Sample ID (e.g. P1_N-LMFP)",
                            value=str(record.get("verified_sample_id") or ""),
                            key=f"review_{index}_v_sample_id",
                            help="Unique sample ID within the publication."
                        )
                        record["verified_source_detail"] = st.text_input(
                            "Source Table / Figure",
                            value=str(record.get("verified_source_detail") or ""),
                            key=f"review_{index}_v_source_detail",
                            help="Specific table, row, or figure in the paper."
                        )

                    record["verified_paper_title"] = st.text_input(
                        "Verified Paper Title",
                        value=str(record.get("verified_paper_title") or ""),
                        key=f"review_{index}_v_paper_title",
                    )

                    st.markdown("###### Rate-Specific Discharge Capacities (mAh/g)")
                    c_c1, c_c2, c_c3 = st.columns(3)
                    with c_c1:
                        record["verified_capacity_0_1c"] = st.text_input(
                            "0.1C Capacity (mAh/g)",
                            value=str(record.get("verified_capacity_0_1c") or ""),
                            key=f"review_{index}_v_cap_0_1c",
                        )
                    with c_c2:
                        record["verified_capacity_1c"] = st.text_input(
                            "1.0C Capacity (mAh/g)",
                            value=str(record.get("verified_capacity_1c") or ""),
                            key=f"review_{index}_v_cap_1c",
                        )
                    with c_c3:
                        record["verified_capacity_5c"] = st.text_input(
                            "5.0C Capacity (mAh/g)",
                            value=str(record.get("verified_capacity_5c") or ""),
                            key=f"review_{index}_v_cap_5c",
                        )

                    st.markdown("###### Capacity Retention Disambiguation")
                    st.caption(
                        "If multiple cycling conditions were extracted, all measurements are preserved. "
                        "Specify the verified benchmark condition below to map into the single benchmark target."
                    )
                    c_r1, c_r2, c_r3 = st.columns(3)
                    with c_r1:
                        record["benchmark_retention_percent"] = st.text_input(
                            "Benchmark Retention (%)",
                            value=str(record.get("benchmark_retention_percent") or ""),
                            key=f"review_{index}_v_ret_pct",
                            help="Single numeric retention percentage (e.g. 89.45)."
                        )
                    with c_r2:
                        record["benchmark_cycle_count"] = st.text_input(
                            "Benchmark Cycles (e.g. 500)",
                            value=str(record.get("benchmark_cycle_count") or ""),
                            key=f"review_{index}_v_cycles",
                        )
                    with c_r3:
                        record["benchmark_c_rate"] = st.text_input(
                            "Benchmark C-rate (e.g. 0.1C)",
                            value=str(record.get("benchmark_c_rate") or ""),
                            key=f"review_{index}_v_crate",
                        )

                    record["retention_condition_verified"] = st.checkbox(
                        "Confirm verified benchmark cycling condition",
                        value=bool(record.get("retention_condition_verified", False)),
                        key=f"review_{index}_v_ret_verified",
                        help="Must be checked to confirm disambiguation of multi-condition retention."
                    )

                    record["page"] = original_record.get("page")

                    col1, col2, col3 = st.columns(3)

                    review_key = (
                        f"{st.session_state.get('lmfp_pdf_name', 'unknown.pdf')}"
                        f"_record_{index}_page_{record.get('page', '?')}"
                    )

                    with col1:
                        if st.button(
                            "Save Pending",
                            key=f"pending_{index}",
                        ):
                            review_id, created = _save_or_update_review(
                                record=record,
                                status="pending",
                                review_key=review_key,
                            )

                            action = "Saved" if created else "Updated"
                            st.success(
                                f"{action} pending review (ID {review_id})."
                            )

                    with col2:
                        if st.button(
                            "Approve",
                            key=f"approve_{index}",
                        ):
                            review_id, created = _save_or_update_review(
                                record=record,
                                status="approved",
                                review_key=review_key,
                            )

                            action = "Saved" if created else "Updated"
                            st.success(
                                f"{action} approved review (ID {review_id})."
                            )

                    with col3:
                        if st.button(
                            "Reject",
                            key=f"reject_{index}",
                        ):
                            review_id, created = _save_or_update_review(
                                record=record,
                                status="rejected",
                                review_key=review_key,
                            )

                            action = "Saved" if created else "Updated"
                            st.warning(
                                f"{action} rejected review (ID {review_id})."
                            )

        if document_result["page_results"]:
            with st.expander("Other page-level results"):
                for item in document_result["page_results"]:
                    st.markdown(f"**PDF page {item['page']}**")
                    st.json(item["data"])

        if document_result["errors"]:
            with st.expander("Extraction errors"):
                st.json(document_result["errors"])


    if not pages:
        return

    candidate_numbers = st.session_state.get(
        "lmfp_candidate_pages", []
    )

    if not candidate_numbers:
        st.warning("No pages with the selected keywords were found.")
        return

    selected_page = st.selectbox(
        "Select a page to extract",
        options=candidate_numbers,
        format_func=lambda number: f"Page {number}",
        key="lmfp_selected_page",
    )

    page_data = next(
        page for page in pages if page["page"] == selected_page
    )

    with st.expander("View extracted page text"):
        st.text(page_data["text"][:12000])

    if st.button(
        "Extract Selected Page",
        key="extract_selected_lmfp_page",
    ):
        try:
            with st.spinner(
                f"Qwen is analysing page {selected_page}..."
            ):
                result = extract_lmfp_data(
                    page_data["text"],
                    selected_page,
                )

            st.session_state["lmfp_extraction_results"] = {
                "page": selected_page,
                "data": result,
            }

        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))

    extraction = st.session_state.get("lmfp_extraction_results")

    if extraction:
        st.subheader(
            f"Extraction results — Page {extraction['page']}"
        )

        st.warning(
            "These are unverified AI-extracted values. "
            "Check them against the original paper before approval."
        )

        st.json(extraction["data"])

        st.caption(
            "This prototype displays results only. Persistent "
            "approval/rejection storage will be added separately."
        )