"""Persistent analytics dashboard for the active business workspace."""
import pandas as pd
import plotly.express as px
import streamlit as st

from src.business_storage import initialize_storage, load_workspace_datasets

st.title("📈 My Business Analytics Dashboard")
workspace = st.session_state.get("active_business_workspace")
if not workspace:
    st.info("Open your business workspace first to view its saved analytics.")
    st.page_link("platform_pages/business_workspace.py", label="Open Business Workspace", icon=":material/business:")
    st.stop()

try:
    initialize_storage()
    tables, metadata = load_workspace_datasets(workspace["workspace_id"])
except Exception as exc:
    st.error(f"Could not load saved business data: {exc}")
    st.stop()

st.caption(f"{workspace['workspace_name']} · {workspace['workspace_type']} · Persistent PostgreSQL data")
if not tables:
    st.info("No saved datasets yet. Upload Customers and Orders to get started.")
    st.page_link("platform_pages/business_workspace.py", label="Go to Upload Centre", icon=":material/upload_file:")
    st.stop()

customers, orders = tables.get("Customers", pd.DataFrame()), tables.get("Orders", pd.DataFrame())
payments, items, products = tables.get("Payments", pd.DataFrame()), tables.get("Order items", pd.DataFrame()), tables.get("Products", pd.DataFrame())
customer_count = customers["customer_id"].nunique() if "customer_id" in customers else None
order_count = orders["order_id"].nunique() if "order_id" in orders else None
revenue, revenue_label = None, None
if "payment_value" in payments:
    revenue, revenue_label = payments["payment_value"].sum(min_count=1), "Payment values"
elif "price" in items:
    revenue, revenue_label = items["price"].sum(min_count=1), "Order-item prices"

c1, c2, c3 = st.columns(3)
c1.metric("Customers", f"{customer_count:,}" if customer_count is not None else "Not supplied")
c2.metric("Orders", f"{order_count:,}" if order_count is not None else "Not supplied")
c3.metric("Revenue", f"{revenue:,.2f}" if revenue is not None and pd.notna(revenue) else "Not available")
if revenue_label:
    st.caption(f"Revenue is calculated from {revenue_label}. Currency is not inferred from uploaded files.")

if {"order_purchase_timestamp", "order_id"}.issubset(orders.columns):
    dated = orders.dropna(subset=["order_purchase_timestamp"]).copy()
    if not dated.empty:
        dated["month"] = dated["order_purchase_timestamp"].dt.to_period("M").astype(str)
        trend = dated.groupby("month", as_index=False)["order_id"].nunique().rename(columns={"order_id": "orders"})
        st.plotly_chart(px.line(trend, x="month", y="orders", markers=True, title="Orders by month"), use_container_width=True)
if "order_status" in orders:
    status = orders["order_status"].fillna("Unknown").value_counts().rename_axis("status").reset_index(name="orders")
    st.plotly_chart(px.bar(status, x="status", y="orders", title="Orders by status"), use_container_width=True)
if "product_category_name" in products:
    category = products["product_category_name"].fillna("Unknown").value_counts().head(15).rename_axis("category").reset_index(name="products")
    st.plotly_chart(px.bar(category, x="category", y="products", title="Product categories"), use_container_width=True)

st.subheader("Saved datasets and exports")
for name, frame in tables.items():
    with st.expander(f"{name} · {len(frame):,} rows"):
        st.caption(f"Source: {metadata[name]['filename']} · Last saved: {metadata[name]['updated_at']}")
        st.dataframe(frame.head(100), use_container_width=True, hide_index=True)
        st.download_button(f"Download {name} as CSV", frame.to_csv(index=False).encode("utf-8"),
                           file_name=f"{name.lower().replace(' ', '_')}_normalized.csv", mime="text/csv", key=f"download_{name}")
st.page_link("platform_pages/business_workspace.py", label="Manage workspace and datasets", icon=":material/settings:")
st.warning("Workspace access currently uses a shared secret key. Individual user accounts, role-based permissions, invitations, audit logs and production-grade tenant controls are not yet implemented.")
