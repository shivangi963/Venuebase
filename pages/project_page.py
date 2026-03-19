import streamlit as st
import pandas as pd
from pages.ui_helpers import apply_global_styles, nav_bar, go_to
from auth.auth_utils import get_project, save_questions_to_project
from rag.document_loader import extract_text, chunk_text, parse_questionnaire
from rag.vector_store import FAISSVectorStore
from rag.answering_engine import answer_all_questions, regenerate_selected



ALLOWED_REF_TYPES = ["pdf", "txt"]
ALLOWED_Q_TYPES   = ["csv", "xlsx", "xls"]


def _get_vs() -> FAISSVectorStore | None:
    return st.session_state.get("vector_store")


def _set_vs(vs: FAISSVectorStore):
    st.session_state["vector_store"] = vs


def _get_results() -> list[dict]:
    return st.session_state.get("results", [])


def _set_results(results: list[dict]):
    st.session_state["results"] = results


def _get_questions() -> list[dict]:
    return st.session_state.get("parsed_questions", [])


def _set_questions(questions: list[dict]):
    st.session_state["parsed_questions"] = questions


def render():
    apply_global_styles()
    nav_bar()

    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning("No project selected. Returning to dashboard.")
        go_to("dashboard")

    project = get_project(project_id)
    if not project:
        st.error("Project not found. It may have been deleted.")
        go_to("dashboard")

    col_title, col_back = st.columns([8, 1])
    with col_title:
        st.markdown(f"## {project['project_name']}")
    with col_back:
        if st.button("← Dashboard", key="back_dash"):
            for k in ["vector_store", "results", "parsed_questions"]:
                st.session_state.pop(k, None)
            go_to("dashboard")

    st.markdown("---")

    if not _get_results() and project.get("questions"):
        _set_results(project["questions"])
        st.info(
            "Loaded previously saved answers. "
            "You can re-upload documents and regenerate if needed.",
        )


    _phase_upload(project_id)
    st.markdown("---")
    _phase_generate(project_id)

    if _get_results():
        st.markdown("---")
        _phase_review(project_id)



def _phase_upload(project_id: str):
    st.markdown("### Step 1 — Upload Documents")

    col_ref, col_q = st.columns(2)

    with col_ref:
        st.markdown("#### Reference Documents")
        st.caption(
            "Upload your venue's policy and spec files. "
            "Supported: PDF, TXT. Upload multiple files."
        )

        ref_files = st.file_uploader(
            "Reference documents",
            type=ALLOWED_REF_TYPES,
            accept_multiple_files=True,
            key="ref_uploader",
            label_visibility="collapsed",
        )

        if ref_files:
            if st.button(
                " Index Reference Documents",
                key="index_docs_btn",
                type="primary",
                use_container_width=True,
            ):
                _index_reference_docs(ref_files)

        vs = _get_vs()
        if vs and vs.index is not None:
            st.success(
                f"{vs.index.ntotal} chunks indexed from "
                f"{len(set(c['source'] for c in vs.chunks))} document(s).",
            )
        else:
            st.info("No documents indexed yet.")

    with col_q:
        st.markdown("#### Questionnaire")
        st.caption(
            "Upload the RFP questionnaire file. "
            "Supported: CSV, XLSX."
        )

        q_file = st.file_uploader(
            "Questionnaire file",
            type=ALLOWED_Q_TYPES,
            accept_multiple_files=False,
            key="q_uploader",
            label_visibility="collapsed",
        )

        if q_file:
            if st.button(
                "Parse Questionnaire",
                key="parse_q_btn",
                type="primary",
                use_container_width=True,
            ):
                _parse_questionnaire_file(q_file)

        questions = _get_questions()
        if questions:
            st.success(
                f" {len(questions)} question(s) parsed.",
            )
            with st.expander("Preview questions"):
                for q in questions:
                    st.markdown(
                        f"**Q{q['question_id']}.** {q['question_text']}"
                    )
        else:
            st.info("No questionnaire loaded yet.")


def _index_reference_docs(ref_files):
    all_chunks = []
    errors     = []

    progress = st.progress(0, text="Reading documents...")

    for i, f in enumerate(ref_files):
        try:
            text   = extract_text(f, f.name)
            chunks = chunk_text(text, source_name=f.name)
            all_chunks.extend(chunks)
        except Exception as e:
            errors.append(f"{f.name}: {e}")

        progress.progress(
            int((i + 1) / len(ref_files) * 50),
            text=f"Parsed {i+1}/{len(ref_files)} files...",
        )

    if errors:
        for err in errors:
            st.warning(f"Skipped — {err}")

    if not all_chunks:
        st.error("No text could be extracted. Please check your files.")
        progress.empty()
        return

    progress.progress(60, text="Building vector index...")

    try:
        vs = FAISSVectorStore()
        vs.build(all_chunks)
        _set_vs(vs)
        progress.progress(100, text="Done!")
        progress.empty()
        st.rerun()
    except Exception as e:
        st.error(f"Failed to build index: {e}")
        progress.empty()


def _parse_questionnaire_file(q_file):
    try:
        questions = parse_questionnaire(q_file, q_file.name)
        _set_questions(questions)
        st.rerun()
    except Exception as e:
        st.error(f"Could not parse questionnaire: {e}")


def _phase_generate(project_id: str):
    st.markdown("### Step 2 — Generate Answers")

    vs        = _get_vs()
    questions = _get_questions()
    ready     = vs is not None and bool(questions)

    if not ready:
        st.info(
            "Complete Step 1 (index reference docs + parse questionnaire) "
            "to enable answer generation.",
        )
        return

    if st.button(
        " Generate All Answers",
        type="primary",
        key="generate_btn",
        use_container_width=False,
    ):
        _run_generation(questions, vs, project_id)


def _run_generation(questions, vs, project_id):
    progress_bar = st.progress(0, text="Starting RAG pipeline...")
    status_text  = st.empty()

    def on_progress(current, total):
        pct = int(current / total * 100)
        progress_bar.progress(pct, text=f"Answering question {current}/{total}...")
        status_text.caption(
            f"Processing: {questions[current - 1]['question_text'][:80]}..."
        )

    try:
        results = answer_all_questions(
            questions=questions,
            vector_store=vs,
            top_k=4,
            progress_callback=on_progress,
        )

        _set_results(results)
        save_questions_to_project(project_id, results)

        progress_bar.progress(100, text="Complete!")
        status_text.empty()
        st.success(" Answers generated and saved to your project.")
        st.rerun()

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Generation failed: {e}")



def _phase_review(project_id: str):
    st.markdown("### Step 3 — Review, Edit & Export")

    results = _get_results()

    _render_coverage_summary(results)

    st.markdown("---")

    df = _results_to_dataframe(results)

    st.markdown("####  Review & Edit Answers")
    st.caption(
        "Edit answers in the **AI Answer** column before exporting. "
        "Use the **Regenerate** checkbox to re-run specific questions."
    )

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Q#": st.column_config.NumberColumn(
                "Q#",
                width="small",
                disabled=True,
            ),
            "Question": st.column_config.TextColumn(
                "Question",
                width="large",
                disabled=True,
            ),
            "AI Answer": st.column_config.TextColumn(
                "AI Answer (Editable)",
                width="large",
            ),
            "Citation": st.column_config.TextColumn(
                "Source",
                width="medium",
                disabled=True,
            ),
            "Status": st.column_config.TextColumn(
                "Status",
                width="small",
                disabled=True,
            ),
            "Confidence": st.column_config.ProgressColumn(
                "Confidence",
                width="small",
                min_value=0,
                max_value=1,
                format="%.0%",
            ),
            "Regenerate": st.column_config.CheckboxColumn(
                "Regenerate?",
                width="small",
                default=False,
            ),
        },
        key="review_table",
    )

    _render_evidence_snippets(results)

    st.markdown("---")

    col_save, col_regen, col_export_csv, col_export_xlsx = st.columns(4)

    with col_save:
        if st.button(
            "Save Edits",
            use_container_width=True,
            key="save_edits_btn",
        ):
            _save_edits(edited_df, project_id)

    with col_regen:
        vs = _get_vs()
        regen_disabled = vs is None
        if st.button(
            " Regenerate Selected",
            use_container_width=True,
            key="regen_btn",
            disabled=regen_disabled,
            help="Select rows above with the Regenerate checkbox first."
            if not regen_disabled
            else "Re-index documents first to enable regeneration.",
        ):
            _run_partial_regeneration(edited_df, project_id)

    with col_export_csv:
        csv_bytes = _prepare_csv(edited_df)
        st.download_button(
            label="⬇Export CSV",
            data=csv_bytes,
            file_name=f"rfp_answers.csv",
            mime="text/csv",
            use_container_width=True,
            key="export_csv_btn",
        )

    with col_export_xlsx:
        from utils.export import prepare_xlsx
        xlsx_bytes = prepare_xlsx(edited_df)
        st.download_button(
            label="⬇Export XLSX",
            data=xlsx_bytes,
            file_name=f"rfp_answers.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="export_xlsx_btn",
        )



def _render_coverage_summary(results: list[dict]):
    total      = len(results)
    answered   = sum(1 for r in results if r.get("status") == "answered")
    not_found  = sum(1 for r in results if r.get("status") == "not_found")
    manual     = total - answered - not_found

    st.markdown("#### Coverage Summary")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        label="Total Questions",
        value=total,
    )
    c2.metric(
        label="Answered with Citations",
        value=answered,
        delta=f"{answered/total*100:.0f}%" if total else "0%",
        delta_color="normal",
    )
    c3.metric(
        label="Not Found in References",
        value=not_found,
        delta=f"{not_found/total*100:.0f}%" if total else "0%",
        delta_color="inverse",
    )
    c4.metric(
        label="Manually Edited",
        value=manual,
    )


#  EVIDENCE SNIPPETS

def _render_evidence_snippets(results: list[dict]):
    with st.expander(" View Evidence Snippets (retrieved source chunks)"):
        st.caption(
            "These are the raw text excerpts retrieved from your reference "
            "documents for each question. They show exactly what context the "
            "AI used to generate each answer."
        )

        for r in results:
            evidence = r.get("evidence", [])
            st.markdown(
                f"**Q{r.get('question_id', '?')}.** {r['question_text']}"
            )

            if not evidence:
                st.caption("— No evidence chunks retrieved.")
            else:
                for i, snippet in enumerate(evidence):
                    st.markdown(
                        f"""
                        <div style="
                            background:#f8f9fa;
                            border-left: 3px solid #4a90d9;
                            padding: 8px 12px;
                            border-radius: 4px;
                            font-size: 0.85rem;
                            color: #333;
                            margin-bottom: 6px;
                        ">
                        <strong>Snippet {i+1}:</strong> {snippet[:400]}{'...' if len(snippet) > 400 else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("---")


#  DATAFRAME HELPERS

def _results_to_dataframe(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        score = r.get("top_score", 0.0)

        confidence = min(max(score, 0.0), 1.0)

        rows.append({
            "Q#"         : r.get("question_id", ""),
            "Question"   : r.get("question_text", ""),
            "AI Answer"  : r.get("ai_answer", ""),
            "Citation"   : r.get("citation", ""),
            "Status"     : r.get("status", ""),
            "Confidence" : round(confidence, 2),
            "Regenerate" : False,
        })

    return pd.DataFrame(rows)


def _dataframe_to_results(df: pd.DataFrame, original_results: list[dict]) -> list[dict]:
    original_map = {r["question_id"]: r for r in original_results}
    updated = []

    for _, row in df.iterrows():
        q_id     = int(row["Q#"])
        original = original_map.get(q_id, {})

        new_answer = str(row["AI Answer"]).strip()
        old_status = original.get("status", "not_found")
        if old_status == "not_found" and new_answer != "Not found in references.":
            new_status = "manual"
        else:
            new_status = old_status

        updated.append({
            "question_id"  : q_id,
            "question_text": str(row["Question"]),
            "ai_answer"    : new_answer,
            "citation"     : str(row["Citation"]),
            "status"       : new_status,
            "evidence"     : original.get("evidence", []),
            "top_score"    : original.get("top_score", 0.0),
        })

    return updated



def _save_edits(edited_df: pd.DataFrame, project_id: str):
    original_results = _get_results()
    updated_results  = _dataframe_to_results(edited_df, original_results)
    _set_results(updated_results)
    save_questions_to_project(project_id, updated_results)
    st.success("Edits saved successfully.")
    st.rerun()


def _run_partial_regeneration(edited_df: pd.DataFrame, project_id: str):
    vs = _get_vs()
    if vs is None:
        st.error("No vector store found. Please re-index your reference documents.")
        return

    regen_rows = edited_df[edited_df["Regenerate"] == True]
    if regen_rows.empty:
        st.warning("No rows selected for regeneration. Tick the Regenerate checkbox.")
        return

    selected_ids = regen_rows["Q#"].astype(int).tolist()

    with st.spinner(
        f"Regenerating {len(selected_ids)} question(s)..."
    ):
        original_results = _get_results()
        updated_results  = regenerate_selected(
            all_results  = original_results,
            selected_ids = selected_ids,
            vector_store = vs,
            top_k        = 4,
        )

    _set_results(updated_results)
    save_questions_to_project(project_id, updated_results)
    st.success(
        f" Regenerated {len(selected_ids)} answer(s) and saved."
    )
    st.rerun()


def _prepare_csv(df: pd.DataFrame) -> bytes:
    export_df = df.drop(columns=["Regenerate"], errors="ignore")
    return export_df.to_csv(index=False).encode("utf-8")
