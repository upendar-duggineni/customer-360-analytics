import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.db_connection import engine

st.set_page_config(
    page_title="Customer 360 Analytics",
    page_icon="📊",
    layout="wide"
)

# ============================================================
# THEME — "Control Tower"
# Dark navy sidebar (control panel) + light data plane (main area),
# emerald/gold accents, monospace KPI numbers for an instrument-panel feel.
# Colors mirror .streamlit/config.toml — keep both in sync if changed.
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3, h4 {
    font-family: 'Sora', sans-serif !important;
    letter-spacing: -0.01em;
}

/* Sidebar — dark control panel */
section[data-testid="stSidebar"] {
    background-color: #12172B;
    border-right: 1px solid #1E2540;
}
section[data-testid="stSidebar"] * {
    color: #E8EAF2 !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-family: 'Sora', sans-serif !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stCaption, 
section[data-testid="stSidebar"] small {
    color: #8891AD !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #232B4A;
}
/* Sidebar select/input controls */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: #1A2140;
    border-color: #2A335A;
}

/* Metric cards — instrument-panel style */
div[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-top: 3px solid #0E7C66;
    border-radius: 10px;
    padding: 14px 16px 10px 16px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    overflow: visible;
}
div[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
    color: #12172B;
    font-size: 1.35rem;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
    line-height: 1.25;
}
div[data-testid="stMetricValue"] > div {
    overflow: visible !important;
    text-overflow: clip !important;
    white-space: normal !important;
}
div[data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    color: #4B5568;
}

/* Widen sidebar so the date-range input isn't clipped */
section[data-testid="stSidebar"] {
    min-width: 340px !important;
    max-width: 380px !important;
}
section[data-testid="stSidebar"] div[data-baseweb="input"] input {
    font-size: 0.82rem;
}

/* Sidebar mini KPI summary cards */
.sidebar-kpi {
    background-color: #1A2140;
    border: 1px solid #2A335A;
    border-left: 3px solid #D9A441;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 8px;
}
.sidebar-kpi .label {
    font-size: 0.72rem;
    color: #8891AD;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.sidebar-kpi .value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.05rem;
    font-weight: 600;
    color: #FFFFFF;
}

/* Insight callout */
div[data-testid="stAlert"] {
    border-radius: 8px;
    border-left: 3px solid #D9A441;
}

/* Tighter divider spacing */
hr {
    margin-top: 0.6rem;
    margin-bottom: 0.6rem;
}
</style>
""", unsafe_allow_html=True)

SEGMENT_ORDER = [
    "Champions",
    "Loyal Customers",
    "Potential Loyalists",
    "At Risk",
    "Hibernating",
    "Needs Attention",
]

SEGMENT_COLORS = {
    "Champions": "#2ca02c",
    "Loyal Customers": "#1f77b4",
    "Potential Loyalists": "#17becf",
    "At Risk": "#ff7f0e",
    "Hibernating": "#d62728",
    "Needs Attention": "#7f7f7f",
}

st.title("📊 Customer 360 Analytics Platform")
st.markdown("### Customer Intelligence & Business Performance Dashboard")
st.caption("Data source: Olist Brazilian E-Commerce dataset (2016–2018)")
st.divider()

# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.markdown("""
<div style="padding: 4px 0 12px 0;">
    <div style="font-family:'Sora',sans-serif; font-size:1.15rem; font-weight:700; color:#FFFFFF;">
        📊 Customer 360
    </div>
    <div style="font-size:0.75rem; color:#8891AD; letter-spacing:0.03em;">
        ANALYTICS CONTROL PANEL
    </div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()
st.sidebar.header("🎛️ Dashboard Filters")

@st.cache_data(ttl=600)
def load_filter_values():
    dates = pd.read_sql(
        """
        SELECT MIN(order_purchase_timestamp)::date AS min_date,
               MAX(order_purchase_timestamp)::date AS max_date
        FROM orders
        """,
        engine,
    )
    states = pd.read_sql(
        """
        SELECT DISTINCT customer_state
        FROM customers
        WHERE customer_state IS NOT NULL
        ORDER BY customer_state
        """,
        engine,
    )
    payment_types = pd.read_sql(
        """
        SELECT DISTINCT payment_type
        FROM payments
        WHERE payment_type IS NOT NULL
        ORDER BY payment_type
        """,
        engine,
    )
    return dates, states, payment_types

try:
    with st.spinner("Loading filter options..."):
        date_info, state_data, payment_data = load_filter_values()
except Exception:
    st.error("⚠️ Unable to load dashboard filters. Check PostgreSQL.")
    st.stop()

min_date = date_info["min_date"].iloc[0]
max_date = date_info["max_date"].iloc[0]

date_range = st.sidebar.date_input(
    "📅 Order Date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

selected_state = st.sidebar.selectbox(
    "🌎 Customer State",
    ["All"] + state_data["customer_state"].tolist(),
)

selected_segment = st.sidebar.selectbox(
    "🎯 Customer Segment",
    ["All"] + SEGMENT_ORDER,
)

selected_payment = st.sidebar.selectbox(
    "💳 Payment Type",
    ["All"] + payment_data["payment_type"].tolist(),
)

st.sidebar.caption(
    "Segment and payment-type filters apply to every section below, "
    "including RFM, Product, Payment, and Delivery analytics."
)

if st.sidebar.button("🔄 Reset Filters"):
    st.rerun()

# ============================================================
# COMMON FILTERS
# ------------------------------------------------------------
# IMPORTANT: segment and payment-type filters use EXISTS subqueries
# rather than JOINs. Joining `payments` (or `customer_rfm_view`)
# directly into a query that also joins `order_items` would fan-out
# rows for any order with multiple payment rows (split payments) or
# would need extra de-duplication — EXISTS avoids that entirely and
# keeps every aggregate (SUM, AVG, COUNT) correct at the order grain.
# ============================================================

def build_filter(alias_orders="o", alias_customers="c"):
    clauses = [f"{alias_orders}.order_purchase_timestamp::date BETWEEN %(start_date)s AND %(end_date)s"]
    params = {"start_date": start_date, "end_date": end_date}

    if selected_state != "All":
        clauses.append(f"{alias_customers}.customer_state = %(state)s")
        params["state"] = selected_state

    if selected_segment != "All":
        clauses.append(f"""EXISTS (
            SELECT 1 FROM customer_rfm_view rv
            WHERE rv.customer_unique_id = {alias_customers}.customer_unique_id
              AND rv.customer_segment = %(segment)s
        )""")
        params["segment"] = selected_segment

    if selected_payment != "All":
        clauses.append(f"""EXISTS (
            SELECT 1 FROM payments px
            WHERE px.order_id = {alias_orders}.order_id
              AND px.payment_type = %(payment_type)s
        )""")
        params["payment_type"] = selected_payment

    return " AND ".join(clauses), params

filter_clause, filter_params = build_filter()

# ============================================================
# EXECUTIVE KPIs
# ------------------------------------------------------------
# Note: `average_rating` is now computed from the FILTERED order set
# (previously this was a hardcoded global average across ALL reviews,
# ignoring every filter — that was a bug).
# ============================================================

CORE_KPI_QUERY = f"""
SELECT
    ROUND(SUM(p.payment_value), 2) AS total_revenue,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT c.customer_unique_id) AS total_customers,
    ROUND(
        SUM(p.payment_value) /
        NULLIF(COUNT(DISTINCT o.order_id), 0),
        2
    ) AS average_order_value,
    ROUND(AVG(r.review_score), 2) AS average_rating
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN payments p ON o.order_id = p.order_id
LEFT JOIN reviews r ON o.order_id = r.order_id
WHERE {filter_clause}
  AND o.order_status = 'delivered';
"""

@st.cache_data(ttl=600)
def load_core_kpis(query, params):
    return pd.read_sql(query, engine, params=params)

try:
    with st.spinner("Crunching executive KPIs..."):
        core_kpis = load_core_kpis(CORE_KPI_QUERY, filter_params)
except Exception:
    st.error("⚠️ Unable to load executive KPIs.")
    st.stop()

if core_kpis.empty:
    st.warning("No data returned for the selected filters.")
    st.stop()

total_revenue = core_kpis["total_revenue"].iloc[0] or 0
total_orders = core_kpis["total_orders"].iloc[0] or 0
total_customers = core_kpis["total_customers"].iloc[0] or 0
average_order_value = core_kpis["average_order_value"].iloc[0] or 0
average_rating = core_kpis["average_rating"].iloc[0] or 0

# Live pinned summary in the sidebar, reflecting current filters
st.sidebar.divider()
st.sidebar.markdown("""
<div style="font-size:0.75rem; color:#8891AD; letter-spacing:0.03em; margin-bottom:8px;">
    CURRENT VIEW
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown(f"""
<div class="sidebar-kpi">
    <div class="label">Revenue</div>
    <div class="value">R${total_revenue:,.2f}</div>
</div>
<div class="sidebar-kpi">
    <div class="label">Orders</div>
    <div class="value">{int(total_orders):,}</div>
</div>
""", unsafe_allow_html=True)

st.subheader("Executive KPIs")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("💰 Total Revenue", f"R${total_revenue:,.2f}")
with col2:
    st.metric("🛒 Total Orders", f"{int(total_orders):,}")
with col3:
    st.metric("👥 Total Customers", f"{int(total_customers):,}")
with col4:
    st.metric("🧾 Average Order Value", f"R${average_order_value:,.2f}")
with col5:
    st.metric("⭐ Average Rating", f"{average_rating:.2f} / 5")

st.divider()

# ============================================================
# RFM
# ------------------------------------------------------------
# This query itself is always lifetime / unfiltered by date (RFM scores
# are meant to reflect a customer's whole history). The segment filter
# still narrows which single segment is displayed, consistent with it
# now also filtering every other section via build_filter() above.
# ============================================================

RFM_QUERY = """
SELECT customer_segment,
       COUNT(*) AS customer_count,
       ROUND(SUM(monetary), 2) AS total_revenue,
       ROUND(AVG(monetary), 2) AS average_customer_value,
       ROUND(AVG(frequency), 2) AS average_purchase_frequency,
       ROUND(AVG(rfm_total_score), 2) AS average_rfm_score
FROM customer_rfm_view
GROUP BY customer_segment
ORDER BY total_revenue DESC;
"""

@st.cache_data(ttl=600)
def load_rfm_data():
    return pd.read_sql(RFM_QUERY, engine)

try:
    with st.spinner("Loading RFM segmentation..."):
        rfm_data = load_rfm_data()
except Exception:
    st.error("⚠️ Unable to load RFM analytics.")
    st.stop()

if selected_segment != "All":
    rfm_data = rfm_data[
        rfm_data["customer_segment"] == selected_segment
    ].copy()

rfm_data["customer_segment"] = pd.Categorical(
    rfm_data["customer_segment"],
    categories=SEGMENT_ORDER,
    ordered=True,
)
rfm_data = rfm_data.sort_values("customer_segment").reset_index(drop=True)

st.subheader("🎯 Customer RFM Segmentation")
st.caption("Lifetime view — not affected by the date range filter (segment/state/payment filters still apply)")

if not rfm_data.empty:
    top_row = rfm_data.sort_values(
        "total_revenue", ascending=False
    ).iloc[0]

    total_rfm_revenue = rfm_data["total_revenue"].sum()
    share = (
        top_row["total_revenue"] / total_rfm_revenue * 100
        if total_rfm_revenue else 0
    )

    st.info(
        f"💡 **{top_row['customer_segment']}** is the highest-revenue "
        f"segment in the selected RFM view, contributing approximately "
        f"**{share:.1f}%** of represented RFM revenue."
    )

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            rfm_data,
            x="customer_segment",
            y="customer_count",
            title="Customers by Segment",
            text="customer_count",
            color="customer_segment",
            color_discrete_map=SEGMENT_COLORS,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            rfm_data,
            x="customer_segment",
            y="total_revenue",
            title="Revenue by Customer Segment",
            text="total_revenue",
            color="customer_segment",
            color_discrete_map=SEGMENT_COLORS,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Segment Performance")
    st.dataframe(rfm_data, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download RFM Segment Data",
        rfm_data.to_csv(index=False).encode("utf-8"),
        "rfm_segments.csv",
        "text/csv",
    )
else:
    st.info("No RFM data for the selected segment.")

st.divider()

# ============================================================
# SALES ANALYTICS
# ============================================================

st.subheader("📈 Sales Analytics")

MONTHLY_REVENUE_QUERY = f"""
SELECT DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month,
       ROUND(SUM(p.payment_value), 2) AS revenue
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN payments p ON o.order_id = p.order_id
WHERE {filter_clause}
  AND o.order_status = 'delivered'
GROUP BY month
ORDER BY month;
"""

STATE_REVENUE_QUERY = f"""
SELECT c.customer_state AS state,
       ROUND(SUM(p.payment_value), 2) AS revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
WHERE {filter_clause}
  AND o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue DESC;
"""

@st.cache_data(ttl=600)
def load_sales_query(query, params):
    return pd.read_sql(query, engine, params=params)

try:
    with st.spinner("Loading sales trends..."):
        monthly_revenue = load_sales_query(MONTHLY_REVENUE_QUERY, filter_params)
        state_revenue = load_sales_query(STATE_REVENUE_QUERY, filter_params)
except Exception:
    st.error("⚠️ Unable to load sales analytics.")
    monthly_revenue = pd.DataFrame()
    state_revenue = pd.DataFrame()

col1, col2 = st.columns(2)

with col1:
    if not monthly_revenue.empty:
        fig = px.line(
            monthly_revenue,
            x="month",
            y="revenue",
            markers=True,
            title="Monthly Revenue",
        )
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Revenue (R$)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly revenue data for the selected filters.")

with col2:
    if not state_revenue.empty:
        fig = px.bar(
            state_revenue.head(15),
            x="state",
            y="revenue",
            title="Revenue by State — Top 15",
        )
        fig.update_layout(
            xaxis_title="State",
            yaxis_title="Revenue (R$)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No state revenue data for the selected filters.")

if not monthly_revenue.empty or not state_revenue.empty:
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        if not monthly_revenue.empty:
            st.download_button(
                "⬇️ Download Monthly Revenue CSV",
                monthly_revenue.to_csv(index=False).encode("utf-8"),
                "monthly_revenue.csv",
                "text/csv",
            )
    with dl_col2:
        if not state_revenue.empty:
            st.download_button(
                "⬇️ Download State Revenue CSV",
                state_revenue.to_csv(index=False).encode("utf-8"),
                "state_revenue.csv",
                "text/csv",
            )

st.divider()

# ============================================================
# PRODUCT ANALYTICS
# ------------------------------------------------------------
# FIX: removed the `JOIN payments p` that used to sit alongside
# `JOIN order_items oi`. That combination fanned out every order_items
# row once per matching payments row (for orders with split payments),
# inflating revenue, items_sold, and revenue_per_order. Payment-type
# filtering is now handled by the EXISTS clause inside filter_clause,
# so this query only joins tables it actually needs columns from.
# ============================================================

st.subheader("📦 Product Analytics")

PRODUCT_ANALYTICS_QUERY = f"""
SELECT
    COALESCE(
        t.product_category_name_english,
        pr.product_category_name,
        'Unknown'
    ) AS category,
    ROUND(SUM(oi.price), 2) AS revenue,
    COUNT(DISTINCT oi.order_id) AS orders,
    COUNT(*) AS items_sold,
    ROUND(
        SUM(oi.price) /
        NULLIF(COUNT(DISTINCT oi.order_id), 0),
        2
    ) AS revenue_per_order
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products pr ON oi.product_id = pr.product_id
LEFT JOIN product_category_name_translation t
    ON pr.product_category_name = t.product_category_name
WHERE {filter_clause}
  AND o.order_status = 'delivered'
  AND pr.product_category_name IS NOT NULL
GROUP BY
    COALESCE(
        t.product_category_name_english,
        pr.product_category_name,
        'Unknown'
    )
ORDER BY revenue DESC;
"""

@st.cache_data(ttl=600)
def load_product_analytics(query, params):
    return pd.read_sql(query, engine, params=params)

try:
    with st.spinner("Analyzing product categories..."):
        product_analytics = load_product_analytics(
            PRODUCT_ANALYTICS_QUERY, filter_params
        )
except Exception:
    st.error("⚠️ Unable to load product analytics.")
    product_analytics = pd.DataFrame()

if not product_analytics.empty:

    total_categories = len(product_analytics)
    total_items = product_analytics["items_sold"].sum()
    total_product_revenue = product_analytics["revenue"].sum()
    top_category = product_analytics.iloc[0]["category"]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📦 Product Categories", f"{total_categories:,}")
    with col2:
        st.metric("🛍️ Items Sold", f"{int(total_items):,}")
    with col3:
        st.metric("💰 Product Revenue", f"R${total_product_revenue:,.2f}")
    with col4:
        st.metric("🏆 Top Category", top_category)

    top_categories_df = product_analytics.head(10).copy()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            top_categories_df.sort_values("revenue"),
            x="revenue",
            y="category",
            orientation="h",
            text="revenue",
            title="Top 10 Categories by Revenue",
        )
        fig.update_layout(
            xaxis_title="Revenue (R$)",
            yaxis_title="Category",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            top_categories_df.sort_values("items_sold"),
            x="items_sold",
            y="category",
            orientation="h",
            text="items_sold",
            title="Top 10 Categories by Items Sold",
        )
        fig.update_layout(
            xaxis_title="Items Sold",
            yaxis_title="Category",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Category Performance")

    category_table = product_analytics.rename(
        columns={
            "category": "Category",
            "revenue": "Revenue (R$)",
            "orders": "Orders",
            "items_sold": "Items Sold",
            "revenue_per_order": "Revenue / Order (R$)",
        }
    )

    st.dataframe(
        category_table,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Product Analytics CSV",
        product_analytics.to_csv(index=False).encode("utf-8"),
        "product_analytics.csv",
        "text/csv",
    )
else:
    st.info("No product data available for the selected filters.")

st.divider()

# ============================================================
# PAYMENT ANALYTICS
# ============================================================

st.subheader("💳 Payment Analytics")

PAYMENT_QUERY = f"""
SELECT
    p.payment_type,
    COUNT(*) AS transactions,
    ROUND(SUM(p.payment_value), 2) AS total_value,
    ROUND(AVG(p.payment_value), 2) AS average_transaction,
    ROUND(AVG(p.payment_installments), 2) AS average_installments
FROM payments p
JOIN orders o ON p.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE {filter_clause}
  AND o.order_status = 'delivered'
GROUP BY p.payment_type
ORDER BY total_value DESC;
"""

@st.cache_data(ttl=600)
def load_payment_data(query, params):
    return pd.read_sql(query, engine, params=params)

try:
    with st.spinner("Analyzing payment methods..."):
        payment_result = load_payment_data(PAYMENT_QUERY, filter_params)
except Exception:
    st.error("⚠️ Unable to load payment analytics.")
    payment_result = pd.DataFrame()

if not payment_result.empty:

    total_payment_value = payment_result["total_value"].sum()
    total_transactions = payment_result["transactions"].sum()

    payment_result["revenue_share"] = (
        payment_result["total_value"] / total_payment_value * 100
        if total_payment_value else 0
    )

    payment_result["transaction_share"] = (
        payment_result["transactions"] / total_transactions * 100
        if total_transactions else 0
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("💳 Payment Revenue", f"R${total_payment_value:,.2f}")
    with col2:
        st.metric("🔢 Transactions", f"{int(total_transactions):,}")
    with col3:
        st.metric("📊 Payment Methods", f"{len(payment_result):,}")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(
            payment_result,
            names="payment_type",
            values="total_value",
            title="Revenue Share by Payment Method",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            payment_result,
            x="payment_type",
            y="transactions",
            text="transactions",
            title="Transactions by Payment Method",
        )
        st.plotly_chart(fig, use_container_width=True)

    payment_table = payment_result.rename(
        columns={
            "payment_type": "Payment Type",
            "transactions": "Transactions",
            "total_value": "Total Value (R$)",
            "average_transaction": "Average Transaction (R$)",
            "average_installments": "Average Installments",
            "revenue_share": "Revenue Share (%)",
            "transaction_share": "Transaction Share (%)",
        }
    )

    st.dataframe(
        payment_table,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "⬇️ Download Payment Analytics CSV",
        payment_result.to_csv(index=False).encode("utf-8"),
        "payment_analytics.csv",
        "text/csv",
    )
else:
    st.info("No payment data available for the selected filters.")

st.divider()

# ============================================================
# DELIVERY ANALYTICS
# ------------------------------------------------------------
# FIX: removed `LEFT JOIN payments p` from both delivery queries.
# Neither query selects any payment column, and the join caused the
# same fan-out issue as Product Analytics — orders with multiple
# payment rows had their delivery_days and late-flag averaged in more
# than once, skewing average_delivery_days and late_delivery_rate.
# Payment-type filtering is now handled by the EXISTS clause inside
# filter_clause.
# ============================================================

st.subheader("🚚 Delivery Analytics")

DELIVERY_QUERY = f"""
SELECT
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    ROUND(
        AVG(
            EXTRACT(
                EPOCH FROM (
                    o.order_delivered_customer_date
                    - o.order_purchase_timestamp
                )
            ) / 86400
        ),
        2
    ) AS average_delivery_days,
    ROUND(
        100.0 * AVG(
            CASE
                WHEN o.order_delivered_customer_date
                     > o.order_estimated_delivery_date
                THEN 1
                ELSE 0
            END
        ),
        2
    ) AS late_delivery_rate
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE {filter_clause}
  AND o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;
"""

DELIVERY_STATE_QUERY = f"""
SELECT
    c.customer_state AS state,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    ROUND(
        AVG(
            EXTRACT(
                EPOCH FROM (
                    o.order_delivered_customer_date
                    - o.order_purchase_timestamp
                )
            ) / 86400
        ),
        2
    ) AS average_delivery_days,
    ROUND(
        100.0 * AVG(
            CASE
                WHEN o.order_delivered_customer_date
                     > o.order_estimated_delivery_date
                THEN 1
                ELSE 0
            END
        ),
        2
    ) AS late_delivery_rate
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE {filter_clause}
  AND o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY average_delivery_days DESC;
"""

@st.cache_data(ttl=600)
def load_delivery(query, params):
    return pd.read_sql(query, engine, params=params)

try:
    with st.spinner("Calculating delivery performance..."):
        delivery_kpis = load_delivery(DELIVERY_QUERY, filter_params)
        delivery_state = load_delivery(DELIVERY_STATE_QUERY, filter_params)
except Exception:
    st.error("⚠️ Unable to load delivery analytics.")
    delivery_kpis = pd.DataFrame()
    delivery_state = pd.DataFrame()

if not delivery_kpis.empty and delivery_kpis["delivered_orders"].iloc[0]:

    row = delivery_kpis.iloc[0]

    delivered_orders = row["delivered_orders"] or 0
    avg_delivery = row["average_delivery_days"] or 0
    late_rate = row["late_delivery_rate"] or 0
    on_time_rate = max(0, 100 - float(late_rate))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📦 Delivered Orders", f"{int(delivered_orders):,}")
    with col2:
        st.metric("🚚 Avg Delivery", f"{avg_delivery:.1f} days")
    with col3:
        st.metric("⏰ Late Delivery", f"{late_rate:.1f}%")
    with col4:
        st.metric("✅ On-Time Delivery", f"{on_time_rate:.1f}%")

    if not delivery_state.empty:

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                delivery_state.sort_values(
                    "average_delivery_days"
                ).head(15),
                x="average_delivery_days",
                y="state",
                orientation="h",
                title="Average Delivery Time by State",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                delivery_state.sort_values(
                    "late_delivery_rate",
                    ascending=False,
                ).head(15),
                x="late_delivery_rate",
                y="state",
                orientation="h",
                title="Late Delivery Rate by State",
            )
            st.plotly_chart(fig, use_container_width=True)

        delivery_table = delivery_state.rename(
            columns={
                "state": "State",
                "delivered_orders": "Delivered Orders",
                "average_delivery_days": "Avg Delivery Days",
                "late_delivery_rate": "Late Delivery (%)",
            }
        )

        st.dataframe(
            delivery_table,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ Download Delivery Analytics CSV",
            delivery_state.to_csv(index=False).encode("utf-8"),
            "delivery_analytics.csv",
            "text/csv",
        )
else:
    st.info("No delivery data available for the selected filters.")

st.divider()

# ============================================================
# CUSTOMER LOOKUP
# ============================================================

st.subheader("🔎 Look Up a Customer")

lookup_id = st.text_input(
    "Enter a Customer ID to view their full profile",
    placeholder="e.g. a4b417188addbc05b26b72d5e448...",
)

if st.button("View Customer Detail →"):
    if lookup_id.strip():
        st.session_state["lookup_customer_id"] = lookup_id.strip()
        st.switch_page("pages/customer_details.py")
    else:
        st.warning("Enter a customer ID first.")

st.divider()

st.caption(
    "Customer 360 Analytics Platform • PostgreSQL + SQL + "
    "Python + Streamlit + Plotly"
)
