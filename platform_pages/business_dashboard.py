"""Business dashboard populated from datasets saved in the current session."""
import pandas as pd
import plotly.express as px
import streamlit as st

st.title("📈 Business Analytics Dashboard")
st.caption("Your saved company dataset — separate from the Olist demonstration.")

tables = st.session_state.get("business_tables", {})
metadata = st.session_state.get("business_upload_metadata", {})

if not tables:
    st.info("No business datasets have been saved in this session yet.")
    st.page_link(
        "platform_pages/business_workspace.py",
        label="Go to Upload Centre",
        icon=":material/upload_file:",
    )
    st.stop()

st.success(
    f"{len(tables)} dataset(s) saved in this active session. "
    "These are separate from the Olist demo."
)

# Establish the available business-level metrics without assuming every
# company supplies every optional table.
customers = tables.get("Customers", pd.DataFrame())
orders = tables.get("Orders", pd.DataFrame())
payments = tables.get("Payments", pd.DataFrame())
items = tables.get("Order items", pd.DataFrame())
products = tables.get("Products", pd.DataFrame())

customer_count = (
    customers["customer_id"].nunique()
    if "customer_id" in customers else None
)
order_count = orders["order_id"].nunique() if "order_id" in orders else None

revenue = None
revenue_source = None
if not payments.empty and "payment_value" in payments:
    revenue = payments["payment_value"].sum(min_count=1)
    revenue_source = "Payment value"
elif not items.empty and "price" in items:
    revenue = items["price"].sum(min_count=1)
    revenue_source = "Order-item price"

col1, col2, col3 = st.columns(3)
col1.metric("Customers", f"{customer_count:,}" if customer_count is not None else "Not provided")
col2.metric("Orders", f"{order_count:,}" if order_count is not None else "Not provided")
col3.metric("Revenue", f"{revenue:,.2f}" if pd.notna(revenue) else "Not available")

if revenue_source:
    st.caption(f"Revenue shown from {revenue_source}; currency is not inferred.")

if not orders.empty and {"order_purchase_timestamp", "order_id"}.issubset(orders.columns):
    dated = orders.dropna(subset=["order_purchase_timestamp"]).copy()
    if not dated.empty:
        dated["month"] = dated["order_purchase_timestamp"].dt.to_period("M").astype(str)
        monthly = dated.groupby("month", as_index=False)["order_id"].nunique()
        monthly = monthly.rename(columns={"order_id": "orders"})
        st.subheader("Orders over time")
        st.plotly_chart(
            px.line(monthly, x="month", y="orders", markers=True, title="Orders by month"),
            use_container_width=True,
        )

if not orders.empty and "order_status" in orders:
    st.subheader("Order status")
    status = orders["order_status"].fillna("Unknown").value_counts().rename_axis("status").reset_index(name="orders")
    st.plotly_chart(
        px.bar(status, x="status", y="orders", title="Orders by status"),
        use_container_width=True,
    )

if not products.empty and "product_category_name" in products:
    st.subheader("Product categories")
    categories = products["product_category_name"].fillna("Unknown").value_counts().head(15).rename_axis("category").reset_index(name="products")
    st.plotly_chart(
        px.bar(categories, x="category", y="products", title="Top product categories"),
        use_container_width=True,
    )

st.subheader("Saved datasets")
for table_name, dataframe in tables.items():
    info = metadata.get(table_name, {})
    with st.expander(f"{table_name} · {len(dataframe):,} rows", expanded=False):
        st.caption(f"Original file: {info.get('filename', 'Unknown')}")
        st.dataframe(dataframe.head(100), use_container_width=True, hide_index=True)
        st.download_button(
            f"Download normalized {table_name} CSV",
            dataframe.to_csv(index=False).encode("utf-8"),
            file_name=f"{table_name.lower().replace(' ', '_')}_normalized.csv",
            mime="text/csv",
            key=f"download_{table_name}",
        )

st.warning(
    "Session storage only: saved datasets are available while this Streamlit "
    "session remains active. They are not yet stored permanently and may be "
    "lost when the session ends or the server restarts."
)
