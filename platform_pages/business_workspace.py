"""Persistent business workspace, upload, validation and dataset management."""
from io import BytesIO
from pathlib import Path
import re
import pandas as pd
import streamlit as st

from src.business_storage import (
    create_workspace, initialize_storage, open_workspace, save_dataset,
    load_workspace_datasets,
)

TABLES = {
    "Customers": {"required": ["customer_id"], "optional": ["customer_unique_id", "customer_city", "customer_state"]},
    "Orders": {"required": ["order_id", "customer_id", "order_purchase_timestamp"], "optional": ["order_status"]},
    "Order items": {"required": ["order_id", "product_id"], "optional": ["price", "freight_value", "seller_id"]},
    "Products": {"required": ["product_id"], "optional": ["product_category_name"]},
    "Payments": {"required": ["order_id", "payment_value"], "optional": ["payment_type", "payment_installments"]},
}
ALIASES = {
    "customer_id": ["customer id", "customerid", "cust id", "cust_id", "client id", "client_number"],
    "customer_unique_id": ["customer unique id", "customer_unique_id"],
    "customer_city": ["city", "customer city"], "customer_state": ["state", "province", "region"],
    "order_id": ["order id", "orderid", "order_no", "order number", "transaction id", "transaction_id"],
    "order_purchase_timestamp": ["purchase date", "purchase_date", "order date", "order_date", "created_at", "created date"],
    "order_status": ["status", "order status"], "product_id": ["product id", "productid", "sku", "item id", "item_id"],
    "price": ["item price", "unit price", "sale price"], "freight_value": ["shipping", "shipping cost", "delivery charge"],
    "seller_id": ["seller id", "merchant id"], "product_category_name": ["category", "product category", "category_name"],
    "payment_value": ["amount", "total", "total amount", "net amount", "net_amount", "total_price"],
    "payment_type": ["payment method", "method"], "payment_installments": ["installments", "installment_count"],
}

def norm(value):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value).lower())).strip()

def read_file(upload):
    suffix = Path(upload.name).suffix.lower()
    payload = BytesIO(upload.getvalue())
    if suffix == ".csv":
        try:
            return pd.read_csv(payload)
        except UnicodeDecodeError:
            payload.seek(0)
            return pd.read_csv(payload, encoding="latin-1")
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(payload, engine="openpyxl")
    raise ValueError("Please upload a CSV or modern Excel (.xlsx/.xlsm) file.")

def suggest(columns, field):
    lookup = {norm(c): c for c in columns}
    for candidate in [field.replace("_", " ")] + ALIASES.get(field, []):
        if norm(candidate) in lookup:
            return lookup[norm(candidate)]
    return None

def prepare(raw, mapping):
    selected = {source: target for target, source in mapping.items() if source}
    frame = raw[list(selected)].rename(columns=selected).copy()
    if "order_purchase_timestamp" in frame:
        frame["order_purchase_timestamp"] = pd.to_datetime(frame["order_purchase_timestamp"], errors="coerce")
    for field in ["price", "freight_value", "payment_value"]:
        if field in frame:
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
    for field in ["customer_id", "customer_unique_id", "order_id", "product_id", "seller_id"]:
        if field in frame:
            frame[field] = frame[field].astype("string").str.strip()
    return frame

st.title("🏢 Business Data Upload Centre")
st.caption("Your persistent business workspace. Uploaded datasets are stored separately from the Olist demo.")
try:
    initialize_storage()
except Exception as exc:
    st.error("Business storage could not connect to PostgreSQL. Check DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD in your local environment or deployment secrets.")
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
    st.subheader("Open an existing workspace")
    with st.form("open_business_workspace"):
        access_key = st.text_input("Workspace access key", type="password")
        open_clicked = st.form_submit_button("Open workspace")
    if open_clicked:
        try:
            workspace = open_workspace(access_key)
            if workspace:
                st.session_state.active_business_workspace = {
                    **workspace, "access_key": access_key.strip()
                }
                st.rerun()
            else:
                st.error("That workspace key was not recognized.")
        except Exception as exc:
            st.error(f"Could not open workspace: {exc}")
    st.info("The workspace access key is a bearer credential. Anyone who has it can access that workspace. Share it only with trusted team members; role-based accounts and invitations are a later milestone.")
    st.stop()

workspace = st.session_state.active_business_workspace
st.success(f"Workspace: {workspace['workspace_name']} · {workspace['workspace_type']}")
if st.session_state.get("new_workspace_access_key"):
    st.warning("Copy and save this workspace key now. It is shown only once and cannot currently be recovered.")
    st.code(st.session_state["new_workspace_access_key"])
    st.session_state["new_workspace_access_key"] = None
with st.expander("Workspace access"):
    st.caption("Share this access key only with trusted members. The current MVP uses one shared key, not individual user accounts or roles.")
    st.code(workspace["access_key"])
if st.button("Switch workspace / sign out"):
    st.session_state.active_business_workspace = None
    st.rerun()

try:
    saved, metadata = load_workspace_datasets(workspace["workspace_id"])
except Exception as exc:
    st.error(f"Could not load saved workspace datasets: {exc}")
    st.stop()

st.subheader("Upload your business data")
st.write("Upload one file per dataset. Start with Customers and Orders. Products, Order items and Payments are optional.")
tabs = st.tabs(list(TABLES))
for table, tab in zip(TABLES, tabs):
    with tab:
        spec = TABLES[table]
        st.caption("Required: " + ", ".join(spec["required"]) + (" · Optional: " + ", ".join(spec["optional"]) if spec["optional"] else ""))
        upload = st.file_uploader(f"Choose {table} file", type=["csv", "xlsx", "xlsm"], key=f"file_{table}")
        if table in saved:
            st.success(f"Persistent dataset available: {len(saved[table]):,} rows. Uploading and saving a new file replaces this dataset.")
        if upload is None:
            continue
        try:
            raw = read_file(upload)
        except Exception as exc:
            st.error(f"Unable to read file: {exc}")
            continue
        if raw.empty or len(raw.columns) > 150:
            st.error("The file must contain data rows and no more than 150 columns.")
            continue
        st.caption(f"{upload.name} · {len(raw):,} rows · {len(raw.columns)} columns")
        fields = spec["required"] + spec["optional"]
        options = ["— Not provided —"] + list(raw.columns)
        with st.form(f"map_{table}"):
            mapping = {}
            cols = st.columns(2)
            for i, field in enumerate(fields):
                default = suggest(raw.columns, field)
                with cols[i % 2]:
                    choice = st.selectbox(field + (" *" if field in spec["required"] else ""), options,
                                          index=options.index(default) if default in options else 0)
                    mapping[field] = None if choice == options[0] else choice
            submitted = st.form_submit_button("Preview and validate", type="primary", use_container_width=True)
        if submitted:
            missing = [f for f in spec["required"] if not mapping.get(f)]
            used = [v for v in mapping.values() if v]
            if missing:
                st.error("Map required fields: " + ", ".join(missing))
            elif len(used) != len(set(used)):
                st.error("Each source column can only be mapped once.")
            else:
                frame = prepare(raw, mapping)
                issues, warnings = [], []
                for field in spec["required"]:
                    bad = int(frame[field].isna().sum())
                    if bad:
                        issues.append(f"{field}: {bad:,} missing or invalid values")
                key_fields = {"Customers": ["customer_id"], "Orders": ["order_id"], "Products": ["product_id"]}.get(table, [])
                for field in key_fields:
                    dup = int(frame[field].duplicated(keep=False).sum())
                    if dup:
                        warnings.append(f"{field}: {dup:,} rows participate in duplicate keys")
                exact = int(frame.duplicated().sum())
                if exact:
                    warnings.append(f"{exact:,} completely duplicated rows")
                st.session_state[f"pending_{table}"] = {"frame": frame, "issues": issues, "warnings": warnings, "filename": upload.name}
        pending = st.session_state.get(f"pending_{table}")
        if pending is not None:
            frame = pending["frame"]
            st.markdown("**Normalized preview**")
            st.dataframe(frame.head(100), use_container_width=True, hide_index=True)
            a, b, c = st.columns(3)
            a.metric("Rows", f"{len(frame):,}")
            b.metric("Columns", len(frame.columns))
            c.metric("Exact duplicate rows", f"{frame.duplicated().sum():,}")
            for issue in pending["issues"]:
                st.error(issue)
            for warning in pending["warnings"]:
                st.warning(warning)
            if not pending["issues"]:
                if st.button(f"Save {table} permanently to this workspace", type="primary", key=f"save_{table}", use_container_width=True):
                    try:
                        save_dataset(workspace["workspace_id"], table, pending["filename"], frame)
                        st.success(f"{table} saved to PostgreSQL.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save dataset: {exc}")
            else:
                st.info("Correct required-field issues in the source file before saving.")

st.divider()
st.subheader("Saved datasets")
for name, frame in saved.items():
    st.write(f"**{name}** · {len(frame):,} rows · {metadata[name]['filename']}")
if saved:
    st.page_link("platform_pages/business_dashboard.py", label="Open My Business Dashboard", icon=":material/analytics:", width="stretch")
