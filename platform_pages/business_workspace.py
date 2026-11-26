"""Business upload, preview, validation and session save workflow."""
from io import BytesIO
from pathlib import Path
import re
import pandas as pd
import streamlit as st

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
    "customer_id": ["customer id", "customerid", "cust id", "cust_id", "client id", "client_number"],
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

def prepare(raw, mapping, table):
    selected = {source: target for target, source in mapping.items() if source}
    frame = raw[list(selected)].rename(columns=selected).copy()
    for field in ["order_purchase_timestamp"]:
        if field in frame:
            frame[field] = pd.to_datetime(frame[field], errors="coerce")
    for field in ["price", "freight_value", "payment_value"]:
        if field in frame:
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
    for field in ["customer_id", "customer_unique_id", "order_id", "product_id", "seller_id"]:
        if field in frame:
            frame[field] = frame[field].astype("string").str.strip()
    return frame

st.title("🏢 Business Data Upload Centre")
st.caption("Import company data, map columns, preview quality checks and save approved results to your business dashboard.")
st.warning("Prototype storage: uploads are processed in memory and saved only in this active Streamlit session. Do not upload confidential or production personal data yet. Permanent secure storage and company/team access controls are not implemented.")

if "business_tables" not in st.session_state:
    st.session_state.business_tables = {}
if "business_meta" not in st.session_state:
    st.session_state.business_meta = {}

st.subheader("1 · Upload datasets")
st.write("Customers and Orders are the recommended starting point. Other files add richer analysis.")
tabs = st.tabs(list(TABLES))
for table, tab in zip(TABLES, tabs):
    with tab:
        spec = TABLES[table]
        st.caption("Required: " + ", ".join(spec["required"]) + (" · Optional: " + ", ".join(spec["optional"]) if spec["optional"] else ""))
        upload = st.file_uploader(f"Choose {table} file", type=["csv", "xlsx", "xlsm"], key=f"file_{table}")
        if upload is None:
            if table in st.session_state.business_tables:
                st.success("A dataset is already saved for this table in this session. Upload a new file to replace it.")
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
                frame = prepare(raw, mapping, table)
                issues = []
                warnings = []
                for field in spec["required"]:
                    bad = int(frame[field].isna().sum())
                    if bad:
                        issues.append(f"{field}: {bad:,} missing or invalid values")
                key = {"Customers": ["customer_id"], "Orders": ["order_id"], "Products": ["product_id"]}.get(table, [])
                for field in key:
                    dup = int(frame[field].duplicated(keep=False).sum())
                    if dup:
                        warnings.append(f"{field}: {dup:,} rows participate in duplicate keys")
                exact_dups = int(frame.duplicated().sum())
                if exact_dups:
                    warnings.append(f"{exact_dups:,} completely duplicated rows")
                if frame.empty:
                    issues.append("No data rows found.")
                st.session_state[f"pending_{table}"] = {
                    "frame": frame, "issues": issues, "warnings": warnings, "filename": upload.name
                }
        pending = st.session_state.get(f"pending_{table}")
        if pending is not None:
            frame = pending["frame"]
            st.markdown("**2 · Normalized preview**")
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
                if st.button(f"Save {table} to Business Dashboard", type="primary", key=f"save_{table}", use_container_width=True):
                    st.session_state.business_tables[table] = frame.copy()
                    st.session_state.business_meta[table] = {"filename": pending["filename"]}
                    st.success(f"{table} saved for this session.")
                    st.rerun()
            else:
                st.info("Correct required-field issues in the source file before saving.")

st.divider()
st.subheader("3 · Cross-dataset relationship checks")
saved = st.session_state.business_tables
relations = []
if "Orders" in saved and "Customers" in saved:
    known = set(saved["Customers"]["customer_id"].dropna().astype(str))
    orphan = int((~saved["Orders"]["customer_id"].astype(str).isin(known)).sum())
    relations.append(("Orders → Customers", orphan))
if "Order items" in saved and "Orders" in saved:
    known = set(saved["Orders"]["order_id"].dropna().astype(str))
    orphan = int((~saved["Order items"]["order_id"].astype(str).isin(known)).sum())
    relations.append(("Order items → Orders", orphan))
if "Payments" in saved and "Orders" in saved:
    known = set(saved["Orders"]["order_id"].dropna().astype(str))
    orphan = int((~saved["Payments"]["order_id"].astype(str).isin(known)).sum())
    relations.append(("Payments → Orders", orphan))
for label, count in relations:
    (st.success if count == 0 else st.warning)(f"{label}: {count:,} orphan references.")
if not relations:
    st.caption("Save related datasets to enable relationship checks.")

st.divider()
st.metric("Datasets saved in this session", len(saved))
st.metric("Total saved rows", f"{sum(len(df) for df in saved.values()):,}")
if saved:
    st.page_link("platform_pages/business_dashboard.py", label="Open My Business Dashboard", icon=":material/analytics:", width="stretch")
