"""Dashboard for business datasets saved in the active Streamlit session."""
import pandas as pd
import plotly.express as px
import streamlit as st

st.title("📈 My Business Analytics Dashboard")
st.caption("Company-uploaded data only · Separate from the Olist demo")
tables = st.session_state.get("business_tables", {})
meta = st.session_state.get("business_meta", {})
if not tables:
    st.info("No datasets have been saved in this session yet.")
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

st.subheader("Saved datasets and results")
for name, frame in tables.items():
    with st.expander(f"{name} · {len(frame):,} rows"):
        st.caption("Source file: " + meta.get(name, {}).get("filename", "Unknown"))
        st.dataframe(frame.head(100), use_container_width=True, hide_index=True)
        st.download_button(f"Download {name} results as CSV", frame.to_csv(index=False).encode("utf-8"),
                           file_name=f"{name.lower().replace(' ', '_')}_normalized.csv", mime="text/csv", key=f"dl_{name}")
st.warning("Saved results are session-only in this prototype. They disappear when the session expires or the server restarts. Permanent encrypted storage, authentication and tenant isolation are required before real company data is used.")
