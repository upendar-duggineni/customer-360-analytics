"""Universal e-commerce data translation workspace.

Files are profiled before mapping. Mapping suggestions are never accepted
silently: users review and confirm them before canonical rows are saved.
"""
from __future__ import annotations

import hashlib
import json
import pandas as pd
import streamlit as st

from src.business_storage import (
    create_workspace, initialize_storage, open_workspace, save_dataset,
    load_workspace_datasets, save_mapping_profile, load_mapping_profile,
)
from src.data_translation import (
    CANONICAL, load_source_file, guess_table, suggest_mapping, profile_frame,
    detect_ambiguous_dates, canonicalize_frame,
)

st.title("🏢 Business Data Translation Centre")
st.caption("Profile any e-commerce export, confirm its translation into our canonical model, and save validated data to your workspace.")

try:
    initialize_storage()
except Exception as exc:
    st.error("Business storage could not connect to PostgreSQL. Check your database environment variables.")
    st.exception(exc)
    st.stop()

if "active_business_workspace" not in st.session_state:
    st.session_state.active_business_workspace = None

if st.session_state.active_business_workspace is None:
    st.subheader("Create a workspace")
    with st.form("create_business_workspace"):
        name = st.text_input("Workspace name", placeholder="e.g. Acme Retail")
        kind = st.selectbox("Workspace type", ["Individual", "Company"])
        create = st.form_submit_button("Create workspace", type="primary")
    if create:
        try:
            workspace = create_workspace(name, kind)
            st.session_state.active_business_workspace = {
                "workspace_id": workspace["workspace_id"],
                "workspace_name": workspace["workspace_name"],
                "workspace_type": workspace["workspace_type"],
                "access_key": workspace["access_key"],
            }
            st.session_state["new_workspace_access_key"] = workspace["access_key"]
            st.rerun()
        except Exception as exc:
            st.error(f"Could not create workspace: {exc}")
    st.divider()
    with st.form("open_business_workspace"):
        access_key = st.text_input("Existing workspace access key", type="password")
        open_clicked = st.form_submit_button("Open workspace")
    if open_clicked:
        workspace = open_workspace(access_key)
        if workspace:
            st.session_state.active_business_workspace = {**workspace, "access_key": access_key.strip()}
            st.rerun()
        else:
            st.error("Workspace key not recognized.")
    st.stop()

workspace = st.session_state.active_business_workspace
st.success(f"Workspace: {workspace['workspace_name']} · {workspace['workspace_type']}")
if st.session_state.get("new_workspace_access_key"):
    st.warning("Copy this access key and store it safely. It is shown only once.")
    st.code(st.session_state["new_workspace_access_key"])
    st.session_state["new_workspace_access_key"] = None
with st.expander("Workspace access"):
    st.caption("This MVP uses a shared bearer key, not individual accounts or roles.")
    st.code(workspace["access_key"])
if st.button("Switch workspace / sign out"):
    st.session_state.active_business_workspace = None
    st.rerun()

saved, metadata = load_workspace_datasets(workspace["workspace_id"])
st.divider()
st.header("1 · Upload and profile source data")
st.write("Upload one CSV or Excel workbook. Excel workbooks can contain multiple sheets; process each sheet separately and assign it to a canonical e-commerce table.")
uploaded = st.file_uploader("Choose CSV, XLSX or XLSM", type=["csv", "xlsx", "xlsm"], key="translation_source")

if uploaded is not None:
    try:
        sheets = load_source_file(uploaded)
        sheet_names = list(sheets)
        selected_sheet = st.selectbox("Select a sheet to inspect", sheet_names, key="translation_sheet")
        sheet = sheets[selected_sheet]
        raw = sheet["data"]
        st.caption(f"Detected header row: {sheet['header_row']} · Data rows: {sheet['raw_row_count']:,} · Candidate total rows: {sheet['total_rows_count']:,} · Columns: {len(raw.columns)}")
        if sheet["total_rows_count"]:
            st.warning(f"Detected {sheet['total_rows_count']} possible total/subtotal row(s). They are excluded from the proposed data preview; inspect them before import.")
            st.dataframe(sheet["candidate_total_rows"].head(10), use_container_width=True, hide_index=True)
        if raw.empty:
            st.error("No data rows were detected on this sheet.")
            st.stop()

        suggested_table = guess_table(selected_sheet, raw.columns)
        table_options = list(CANONICAL)
        table_index = table_options.index(suggested_table) if suggested_table in table_options else 0
        table_name = st.selectbox("What does this sheet contain?", table_options, index=table_index, key=f"table_{selected_sheet}")
        proposals, profiles = suggest_mapping(raw, table_name)
        fingerprint_source = "|".join([uploaded.name, selected_sheet, table_name] + [str(c) for c in raw.columns])
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
        saved_mapping = load_mapping_profile(workspace["workspace_id"], fingerprint)
        if saved_mapping:
            st.info("A previously confirmed mapping profile matches this file structure. Review it before confirming again.")
            for field in proposals:
                source = saved_mapping.get(field)
                if source in raw.columns:
                    proposals[field] = {
                        "source_column": source,
                        "confidence": 1.0,
                        "signal": "saved profile",
                        "reason": "Previously confirmed by this workspace",
                    }

        st.subheader("2 · Profile the source columns")
        profile_rows = []
        for column, profile in profiles.items():
            profile_rows.append({
                "Source column": column,
                "Type guess": profile["type_guess"],
                "Non-null": profile["non_null"],
                "Null %": profile["null_pct"],
                "Unique values": profile["unique"],
                "Unique %": profile["unique_pct"],
                "Sample values": " · ".join(profile["samples"][:3]),
            })
        st.dataframe(pd.DataFrame(profile_rows), use_container_width=True, hide_index=True)

        st.subheader("3 · Review and confirm canonical mapping")
        st.caption("Suggestions combine header aliases and value patterns. Confidence is a heuristic, not a probability. Confirm or change every mapping before import.")
        fields = list(CANONICAL[table_name])
        source_options = ["— Unmapped —"] + [str(c) for c in raw.columns]
        chosen = {}
        with st.form(f"confirm_mapping_{selected_sheet}_{table_name}"):
            cols = st.columns(2)
            for index, field in enumerate(fields):
                proposal = proposals.get(field)
                proposed_source = proposal["source_column"] if proposal else None
                default = source_options.index(proposed_source) if proposed_source in source_options else 0
                with cols[index % 2]:
                    label = field.replace("_", " ").title()
                    if proposal:
                        st.caption(f"{label} · {proposal['confidence']:.0%} confidence · {proposal['reason']}")
                    choice = st.selectbox(label, source_options, index=default, key=f"translation_map_{selected_sheet}_{table_name}_{field}")
                    chosen[field] = None if choice == source_options[0] else choice

            llm_consent = st.checkbox(
                "I explicitly opt in to LLM-assisted mapping suggestions for this file",
                value=False,
                help="LLM suggestions may send column names and masked sample values to an external AI provider. They never approve mappings automatically.",
            )
            st.caption("LLM provider integration is not configured in this build. No file data is sent to an external AI service; deterministic local suggestions remain active.")
            confirm = st.form_submit_button("Confirm mapping and validate", type="primary", use_container_width=True)

        if confirm:
            duplicates = [v for v in chosen.values() if v and list(chosen.values()).count(v) > 1]
            if duplicates:
                st.error("A source column is mapped more than once. Resolve duplicate assignments.")
            elif not any(chosen.values()):
                st.error("Map at least one field before continuing.")
            else:
                ambiguous = []
                if chosen.get("order_purchase_timestamp"):
                    ambiguous = detect_ambiguous_dates(raw[chosen["order_purchase_timestamp"]])
                st.session_state["translation_pending"] = {
                    "filename": uploaded.name,
                    "sheet": selected_sheet,
                    "table": table_name,
                    "raw": raw.copy(),
                    "mapping": chosen,
                    "fingerprint": fingerprint,
                    "ambiguous_dates": ambiguous,
                    "llm_consent": llm_consent,
                }

        pending = st.session_state.get("translation_pending")
        if pending and pending["filename"] == uploaded.name and pending["sheet"] == selected_sheet:
            st.subheader("4 · Resolve date, status and currency ambiguity")
            date_format = "dayfirst"
            if pending["ambiguous_dates"]:
                st.warning("Some dates can be interpreted as either day-first or month-first. Choose the correct convention.")
                st.write("Examples:", ", ".join(pending["ambiguous_dates"][:8]))
                date_format = st.radio("Date format", ["dayfirst", "monthfirst"], horizontal=True, format_func=lambda x: "DD/MM/YYYY" if x == "dayfirst" else "MM/DD/YYYY")
            currency = st.selectbox("Currency for this dataset", ["Not specified", "INR", "USD", "BRL", "EUR", "GBP", "Other"])
            if currency == "Other":
                currency = st.text_input("Enter ISO currency code", max_chars=3).upper()
            status_mapping = {}
            if pending["mapping"].get("order_status"):
                source_status = pending["raw"][pending["mapping"]["order_status"]].dropna().astype(str).str.strip().unique().tolist()
                if source_status:
                    st.write("Assign source order statuses to canonical statuses. Unrecognized values must be assigned explicitly.")
                    for status in sorted(source_status)[:100]:
                        normalized = status.lower()
                        default = "Completed" if normalized in {"delivered", "complete", "completed", "fulfilled"} else "Cancelled" if normalized in {"cancelled", "canceled"} else "Returned" if normalized in {"returned", "refunded", "rto"} else "Pending"
                        status_mapping[status] = st.selectbox(
                            f"Source status: {status}",
                            ["Completed", "Pending", "Cancelled", "Returned", "Ignore / Unmapped"],
                            index=["Completed", "Pending", "Cancelled", "Returned", "Ignore / Unmapped"].index(default),
                            key=f"status_{selected_sheet}_{status}",
                        )
            translated = canonicalize_frame(
                pending["raw"], pending["mapping"], pending["table"],
                date_format=date_format,
                status_mapping={k.lower(): v.lower() for k, v in status_mapping.items() if v != "Ignore / Unmapped"},
                currency="" if currency == "Not specified" else currency,
            )
            required = {
                "Customers": ["customer_id"],
                "Orders": ["order_id"],
                "Order items": ["order_id", "product_id"],
                "Products": ["product_id"],
                "Payments": ["order_id"],
                "Reviews": ["review_id"],
            }[pending["table"]]
            rejected_mask = pd.Series(False, index=translated.index)
            rejection_reason = pd.Series("", index=translated.index, dtype="string")
            for field in required:
                if field in translated:
                    bad = translated[field].isna() | translated[field].astype("string").str.strip().eq("")
                    rejected_mask |= bad
                    rejection_reason.loc[bad] = rejection_reason.loc[bad].astype(str) + f"Missing {field}; "
                else:
                    rejected_mask[:] = True
                    rejection_reason[:] = f"Required canonical field {field} was not mapped."
            if pending["table"] == "Orders" and "order_purchase_timestamp" in translated:
                invalid_dates = translated["order_purchase_timestamp"].isna()
                rejected_mask |= invalid_dates
                rejection_reason.loc[invalid_dates] = rejection_reason.loc[invalid_dates].astype(str) + "Unparseable order date; "
            amount_field = "order_total" if "order_total" in translated else "payment_amount" if "payment_amount" in translated else None
            if amount_field:
                negative = pd.to_numeric(translated[amount_field], errors="coerce") < 0
                rejected_mask |= negative
                rejection_reason.loc[negative] = rejection_reason.loc[negative].astype(str) + f"Negative {amount_field}; "
            accepted = translated.loc[~rejected_mask].copy()
            rejected = translated.loc[rejected_mask].copy()
            rejected["rejection_reason"] = rejection_reason.loc[rejected_mask].values

            st.subheader("5 · Review import quality")
            a, b, c = st.columns(3)
            a.metric("Source rows", f"{len(translated):,}")
            b.metric("Accepted rows", f"{len(accepted):,}")
            c.metric("Rejected rows", f"{len(rejected):,}")
            st.dataframe(accepted.head(50), use_container_width=True, hide_index=True)
            if not rejected.empty:
                st.error("Rejected rows are not silently dropped. Download the rejection report, correct the source or mapping, and re-import.")
                st.dataframe(rejected.head(50), use_container_width=True, hide_index=True)
                st.download_button("Download rejected rows and reasons", rejected.to_csv(index=False).encode("utf-8"), "rejected_rows.csv", "text/csv")
            if not accepted.empty:
                if st.button(f"Save {pending['table']} canonical data to workspace", type="primary", key="save_translated_dataset"):
                    try:
                        save_dataset(workspace["workspace_id"], pending["table"], f"{pending['filename']} · {pending['sheet']}", accepted)
                        save_mapping_profile(workspace["workspace_id"], pending["fingerprint"], pending["table"], pending["mapping"])
                        if not rejected.empty:
                            st.session_state["last_rejection_report"] = rejected
                        st.success(f"Saved {len(accepted):,} accepted rows to {pending['table']}. Mapping profile saved for reuse.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save translated data: {exc}")

        st.subheader("6 · Workbook sheet inventory")
        st.caption("Process another sheet by selecting it above. The platform proposes a canonical table for each sheet; confirm or change the table assignment.")
        st.write("Sheets detected:", ", ".join(sheet_names))
    except Exception as exc:
        st.error(f"Could not profile this file: {exc}")
        st.exception(exc)

st.divider()
st.subheader("Saved canonical datasets")
for name, frame in saved.items():
    st.write(f"**{name}** · {len(frame):,} rows · {metadata[name]['filename']}")
if saved:
    st.page_link("platform_pages/business_dashboard.py", label="Open My Business Dashboard", icon=":material/analytics:", width="stretch")
st.warning("This build uses deterministic local mapping only. LLM mapping is opt-in in the interface but external provider integration is not yet connected. No upload data is sent to an LLM.")
