import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.db_connection import engine


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Customer 360 | Entity Detail",
    page_icon="🔍",
    layout="wide",
)

# ============================================================
# THEME
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3, h4 {
    font-family: 'Sora', sans-serif !important;
}

section[data-testid="stSidebar"] {
    background-color: #12172B;
    border-right: 1px solid #1E2540;
}

section[data-testid="stSidebar"] * {
    color: #E8EAF2 !important;
}

div[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-top: 3px solid #0E7C66;
    border-radius: 10px;
    padding: 14px 16px 10px 16px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}

div[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace;
    color: #12172B;
}

div[data-testid="stMetricLabel"] {
    font-weight: 500;
    color: #4B5568;
}

.order-card {
    background: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-left: 4px solid #0E7C66;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 12px;
}

.id-text {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.88rem;
    color: #12172B;
}

.muted {
    color: #667085;
    font-size: 0.88rem;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🔍 Customer 360 Detail")
st.caption(
    "Search by Customer ID, Order ID or Product ID and trace the "
    "complete business relationship."
)

st.divider()


SEGMENT_COLORS = {
    "Champions": "#2ca02c",
    "Loyal Customers": "#1f77b4",
    "Potential Loyalists": "#17becf",
    "At Risk": "#ff7f0e",
    "Hibernating": "#d62728",
    "Needs Attention": "#7f7f7f",
}


# ============================================================
# UNIVERSAL ENTITY SEARCH
# ============================================================

ENTITY_SEARCH_QUERY = """
WITH matches AS (

    SELECT
        'Customer' AS matched_type,
        c.customer_unique_id::text AS matched_id,
        c.customer_unique_id::text AS customer_unique_id,
        NULL::text AS order_id,
        NULL::text AS product_id,
        NULL::text AS seller_id
    FROM customers c
    WHERE c.customer_unique_id::text ILIKE %(term)s

    UNION ALL

    SELECT
        'Customer ID' AS matched_type,
        c.customer_id::text AS matched_id,
        c.customer_unique_id::text AS customer_unique_id,
        NULL::text AS order_id,
        NULL::text AS product_id,
        NULL::text AS seller_id
    FROM customers c
    WHERE c.customer_id::text ILIKE %(term)s

    UNION ALL

    SELECT
        'Order' AS matched_type,
        o.order_id::text AS matched_id,
        c.customer_unique_id::text AS customer_unique_id,
        o.order_id::text AS order_id,
        NULL::text AS product_id,
        NULL::text AS seller_id
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_id::text ILIKE %(term)s

    UNION ALL

    SELECT DISTINCT
        'Product' AS matched_type,
        oi.product_id::text AS matched_id,
        c.customer_unique_id::text AS customer_unique_id,
        oi.order_id::text AS order_id,
        oi.product_id::text AS product_id,
        NULL::text AS seller_id
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE oi.product_id::text ILIKE %(term)s

    UNION ALL

    SELECT
        'Seller' AS matched_type,
        s.seller_id::text AS matched_id,
        NULL::text AS customer_unique_id,
        NULL::text AS order_id,
        NULL::text AS product_id,
        s.seller_id::text AS seller_id
    FROM sellers s
    WHERE s.seller_id::text ILIKE %(term)s
),
unique_matches AS (
    SELECT DISTINCT
        matched_type,
        matched_id,
        customer_unique_id,
        order_id,
        product_id,
        seller_id
    FROM matches
)
SELECT
    matched_type,
    matched_id,
    customer_unique_id,
    order_id,
    product_id,
    seller_id
FROM unique_matches
ORDER BY
    CASE matched_type
        WHEN 'Customer' THEN 1
        WHEN 'Customer ID' THEN 2
        WHEN 'Order' THEN 3
        WHEN 'Product' THEN 4
        WHEN 'Seller' THEN 5
        ELSE 6
    END,
    matched_id
LIMIT 50;
"""



@st.cache_data(ttl=600)
def search_entities(term: str) -> pd.DataFrame:
    return pd.read_sql(
        ENTITY_SEARCH_QUERY,
        engine,
        params={"term": f"%{term.strip()}%"},
    )


# ============================================================
# PROFILE / ORDER QUERIES
# ============================================================

SELLER_PROFILE_QUERY = """
SELECT
    s.seller_id,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(DISTINCT oi.product_id) AS unique_products,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    ROUND(COALESCE(SUM(oi.price + oi.freight_value), 0)::numeric, 2) AS seller_gmv
FROM sellers s
LEFT JOIN order_items oi ON s.seller_id = oi.seller_id
LEFT JOIN orders o ON oi.order_id = o.order_id
WHERE s.seller_id = %(sid)s
GROUP BY
    s.seller_id,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state;
"""

SELLER_ORDERS_QUERY = """
SELECT
    o.order_id,
    c.customer_unique_id,
    o.order_purchase_timestamp::date AS order_date,
    o.order_status,
    COUNT(DISTINCT oi.order_item_id) AS items,
    ROUND(COALESCE(SUM(oi.price + oi.freight_value), 0)::numeric, 2) AS seller_order_value
FROM sellers s
JOIN order_items oi ON s.seller_id = oi.seller_id
JOIN orders o ON oi.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE s.seller_id = %(sid)s
GROUP BY
    o.order_id,
    c.customer_unique_id,
    o.order_purchase_timestamp,
    o.order_status
ORDER BY o.order_purchase_timestamp DESC;
"""

PROFILE_QUERY = """
SELECT
    r.customer_unique_id,
    c.customer_id,
    c.customer_city,
    c.customer_state,
    r.customer_segment,
    r.monetary,
    r.frequency,
    r.rfm_total_score,
    r.last_purchase_date,
    r.recency_score,
    r.frequency_score,
    r.monetary_score
FROM customer_rfm_view r
JOIN customers c
    ON c.customer_unique_id = r.customer_unique_id
WHERE r.customer_unique_id = %(cid)s
LIMIT 1;
"""


ORDER_HISTORY_QUERY = """
SELECT
    o.order_id,
    o.order_purchase_timestamp::date AS order_date,
    o.order_status,
    COALESCE(SUM(p.payment_value), 0) AS payment_value,
    STRING_AGG(DISTINCT p.payment_type, ', ') AS payment_type,
    MAX(r.review_score) AS review_score
FROM customers c
JOIN orders o
    ON c.customer_id = o.customer_id
LEFT JOIN payments p
    ON o.order_id = p.order_id
LEFT JOIN reviews r
    ON o.order_id = r.order_id
WHERE c.customer_unique_id = %(cid)s
GROUP BY
    o.order_id,
    o.order_purchase_timestamp,
    o.order_status
ORDER BY o.order_purchase_timestamp DESC;
"""


# Aggregated CTEs prevent payment/review joins from multiplying
# product rows and inflating order totals.
ORDER_DETAILS_QUERY = """
WITH payment_summary AS (
    SELECT
        order_id,
        STRING_AGG(DISTINCT payment_type, ', ') AS payment_type,
        MAX(payment_installments) AS payment_installments,
        SUM(payment_value) AS payment_value
    FROM payments
    GROUP BY order_id
),
review_summary AS (
    SELECT DISTINCT ON (order_id)
        order_id,
        review_id,
        review_score,
        review_comment_title,
        review_comment_message
    FROM reviews
    ORDER BY order_id, review_score DESC NULLS LAST
)
SELECT
    o.order_id,
    o.order_purchase_timestamp,
    o.order_status,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    oi.shipping_limit_date,
    oi.price,
    oi.freight_value,

    p.product_category_name,
    pt.product_category_name_english,

    s.seller_city,
    s.seller_state,

    ps.payment_type,
    ps.payment_installments,
    ps.payment_value,

    rs.review_id,
    rs.review_score,
    rs.review_comment_title,
    rs.review_comment_message

FROM orders o

JOIN customers c
    ON o.customer_id = c.customer_id

LEFT JOIN order_items oi
    ON o.order_id = oi.order_id

LEFT JOIN products p
    ON oi.product_id = p.product_id

LEFT JOIN product_category_name_translation pt
    ON p.product_category_name = pt.product_category_name

LEFT JOIN sellers s
    ON oi.seller_id = s.seller_id

LEFT JOIN payment_summary ps
    ON o.order_id = ps.order_id

LEFT JOIN review_summary rs
    ON o.order_id = rs.order_id

WHERE c.customer_unique_id = %(cid)s
  AND o.order_id = %(order_id)s

ORDER BY oi.order_item_id;
"""


@st.cache_data(ttl=600)
def load_seller_profile(sid: str) -> pd.DataFrame:
    return pd.read_sql(
        SELLER_PROFILE_QUERY,
        engine,
        params={"sid": sid},
    )


@st.cache_data(ttl=600)
def load_seller_orders(sid: str) -> pd.DataFrame:
    return pd.read_sql(
        SELLER_ORDERS_QUERY,
        engine,
        params={"sid": sid},
    )


@st.cache_data(ttl=600)
def load_profile(cid: str) -> pd.DataFrame:
    return pd.read_sql(
        PROFILE_QUERY,
        engine,
        params={"cid": cid},
    )


@st.cache_data(ttl=600)
def load_order_history(cid: str) -> pd.DataFrame:
    return pd.read_sql(
        ORDER_HISTORY_QUERY,
        engine,
        params={"cid": cid},
    )


@st.cache_data(ttl=600)
def load_order_details(cid: str, order_id: str) -> pd.DataFrame:
    return pd.read_sql(
        ORDER_DETAILS_QUERY,
        engine,
        params={
            "cid": cid,
            "order_id": order_id,
        },
    )


# ============================================================
# SEARCH INPUT
# ============================================================

search_term = st.text_input(
    "🔎 Search Customer ID / Order ID / Product ID / Seller ID",
    placeholder="Paste a customer_unique_id, order_id, product_id or seller_id...",
    help=(
        "You can now enter a Customer Unique ID, internal Customer ID, "
        "Order ID, Product ID or Seller ID."
    ),
)


# ============================================================
# NO SEARCH
# ============================================================

if not search_term.strip():
    st.info(
        "Enter any Customer ID, Order ID or Product ID above. "
        "The dashboard will automatically identify the entity and "
        "open the connected Customer 360 profile."
    )

    st.markdown("""
    ### 🔗 Supported relationship search

    **Customer ID**
    → Customer Profile → Orders → Products → Sellers → Payments → Reviews

    **Order ID**
    → Order → Customer → Products → Sellers → Payments → Reviews

    **Product ID**
    → Product → Order(s) → Customer → Seller → Payment → Review

    **Seller ID**
    → Seller → Orders → Customers → Products → Payment → Review
    """)

    st.stop()


# ============================================================
# SEARCH RESULTS
# ============================================================

try:
    with st.spinner("Searching across Customer, Order and Product data..."):
        matches = search_entities(search_term)
except Exception as exc:
    st.error(
        "⚠️ Unable to search the database. "
        "Please check your PostgreSQL connection."
    )
    st.stop()


if matches.empty:
    st.warning(
        "No matching Customer ID, Order ID or Product ID was found."
    )
    st.stop()


display_matches = matches.rename(
    columns={
        "matched_type": "Matched Entity",
        "matched_id": "Matched ID",
        "customer_unique_id": "Customer Unique ID",
        "order_id": "Order ID",
        "product_id": "Product ID",
        "seller_id": "Seller ID",
    }
)

st.subheader("🎯 Search Results")

st.dataframe(
    display_matches,
    use_container_width=True,
    hide_index=True,
)

# Build a human-readable selection label.
match_options = matches.index.tolist()

selected_index = st.selectbox(
    "Select the entity you want to explore",
    match_options,
    format_func=lambda idx: (
        f"{matches.loc[idx, 'matched_type']} | "
        f"{matches.loc[idx, 'matched_id']}"
    ),
)

selected_match = matches.loc[selected_index]

matched_type = selected_match["matched_type"]
customer_unique_id = selected_match["customer_unique_id"]
matched_order_id = selected_match["order_id"]

st.success(
    f"Detected **{matched_type}**. "
    f"Opening the connected Customer 360 profile."
)

st.divider()


# ============================================================
# SELLER 360 BRANCH
# ============================================================

matched_seller_id = selected_match["seller_id"]

if matched_type == "Seller":
    st.success(
        "Detected **Seller ID**. Opening the connected Seller 360 profile."
    )

    try:
        with st.spinner("Loading Seller 360 profile..."):
            seller_profile = load_seller_profile(matched_seller_id)
            seller_orders = load_seller_orders(matched_seller_id)
    except Exception as exc:
        st.error("⚠️ Unable to load seller details.")
        st.exception(exc)
        st.stop()

    if seller_profile.empty:
        st.warning("Seller was found, but no seller profile data is available.")
        st.stop()

    seller = seller_profile.iloc[0]

    st.subheader("🏪 Seller 360")

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.metric("🏪 Seller ID", str(seller["seller_id"])[:12] + "…")
    with s2:
        st.metric("📍 City", str(seller["seller_city"]).title())
    with s3:
        st.metric("🗺️ State", str(seller["seller_state"]))
    with s4:
        st.metric("📮 ZIP Prefix", str(seller["seller_zip_code_prefix"]))

    s5, s6, s7, s8 = st.columns(4)

    with s5:
        st.metric("📦 Orders", f"{int(seller['total_orders']):,}")
    with s6:
        st.metric("🛍️ Products", f"{int(seller['unique_products']):,}")
    with s7:
        st.metric("👥 Customers", f"{int(seller['unique_customers']):,}")
    with s8:
        st.metric("💰 Seller GMV", f"R${seller['seller_gmv']:,.2f}")

    st.subheader("📦 Seller Order History")

    if seller_orders.empty:
        st.warning("No orders were found for this seller.")
        st.stop()

    seller_display = seller_orders.rename(
        columns={
            "order_id": "Order ID",
            "customer_unique_id": "Customer Unique ID",
            "order_date": "Date",
            "order_status": "Status",
            "items": "Items",
            "seller_order_value": "Seller Value (R$)",
        }
    )

    st.dataframe(
        seller_display,
        use_container_width=True,
        hide_index=True,
    )

    seller_order_options = seller_orders["order_id"].tolist()

    matched_order_id = st.selectbox(
        "🔎 Select a seller order to open the connected Customer 360",
        seller_order_options,
        format_func=str,
    )

    customer_unique_id = seller_orders.loc[
        seller_orders["order_id"] == matched_order_id,
        "customer_unique_id",
    ].iloc[0]

    st.divider()

else:
    st.success(
        f"Detected **{matched_type}**. "
        "Opening the connected Customer 360 profile."
    )

st.divider()


# ============================================================
# CUSTOMER PROFILE
# ============================================================

try:
    with st.spinner("Loading Customer 360 profile..."):
        profile = load_profile(customer_unique_id)
        orders = load_order_history(customer_unique_id)
except Exception:
    st.error("⚠️ Unable to load customer data.")
    st.stop()


if profile.empty:
    st.warning(
        "This customer does not have an RFM profile yet. "
        "The order/product relationship can still be explored."
    )
else:

    row = profile.iloc[0]
    segment = row["customer_segment"]
    segment_color = SEGMENT_COLORS.get(segment, "#7f7f7f")

    st.subheader("👤 Customer Profile")

    summary_df = pd.DataFrame([{
        "Customer Unique ID": row["customer_unique_id"],
        "Customer ID": row["customer_id"],
        "City": str(row["customer_city"]).title(),
        "State": row["customer_state"],
        "Segment": segment,
        "Total Spend": f"R${row['monetary']:,.2f}",
        "Orders": row["frequency"],
        "RFM": (
            f"{row['rfm_total_score']} "
            f"({row['recency_score']}/"
            f"{row['frequency_score']}/"
            f"{row['monetary_score']})"
        ),
    }])

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "📅 Last Purchase",
            str(row["last_purchase_date"]),
        )

    with c2:
        st.metric(
            "💰 Total Spend",
            f"R${row['monetary']:,.2f}",
        )

    with c3:
        st.metric(
            "🛒 Total Orders",
            f"{int(row['frequency']):,}",
        )

    with c4:
        st.markdown(
            f"""
            <div style="
                padding: 12px 16px;
                border-radius: 8px;
                background-color: {segment_color}22;
                border-left: 6px solid {segment_color};
            ">
                <span style="
                    font-weight: 600;
                    color: {segment_color};
                ">
                    🎯 {segment}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.divider()


# ============================================================
# ORDER HISTORY
# ============================================================

st.subheader("📦 Connected Orders")

if orders.empty:
    st.info("No orders found for this customer.")
    st.stop()


display_orders = orders.rename(
    columns={
        "order_id": "Order ID",
        "order_date": "Date",
        "order_status": "Status",
        "payment_value": "Payment (R$)",
        "payment_type": "Payment Type",
        "review_score": "Review Score",
    }
)

st.dataframe(
    display_orders,
    use_container_width=True,
    hide_index=True,
)

order_options = orders["order_id"].tolist()

# If the user searched an Order ID, automatically select it.
default_order_index = 0
if matched_order_id in order_options:
    default_order_index = order_options.index(matched_order_id)

selected_order = st.selectbox(
    "🔎 Select an Order ID to open Order 360",
    order_options,
    index=default_order_index,
    format_func=str,
)

st.divider()


# ============================================================
# ORDER 360
# ============================================================

st.subheader("🧾 Order 360")

try:
    with st.spinner("Loading order relationships..."):
        order_details = load_order_details(
            customer_unique_id,
            selected_order,
        )
except Exception:
    st.error(
        "⚠️ Unable to load Order 360 details. "
        "Check the PostgreSQL table relationships."
    )
    st.stop()


if order_details.empty:
    st.warning("No detailed records found for this order.")
else:

    first = order_details.iloc[0]

    st.markdown(
        f"""
        <div class="order-card">
            <div class="muted">ORDER ID</div>
            <div class="id-text">{first['order_id']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "📅 Order Date",
            str(first["order_purchase_timestamp"])[:10],
        )

    with c2:
        st.metric(
            "📦 Status",
            str(first["order_status"]).title(),
        )

    with c3:
        order_value = (
            order_details["payment_value"]
            .dropna()
            .iloc[0]
            if not order_details["payment_value"].dropna().empty
            else 0
        )
        st.metric(
            "💰 Order Value",
            f"R${order_value:,.2f}",
        )

    with c4:
        item_count = order_details["order_item_id"].nunique()
        st.metric(
            "🛍️ Items",
            f"{item_count:,}",
        )

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    st.subheader("🛍️ Products in This Order")

    products_df = order_details[
        [
            "order_item_id",
            "product_id",
            "product_category_name_english",
            "price",
            "freight_value",
            "seller_id",
        ]
    ].drop_duplicates(
        subset=["order_item_id"]
    ).copy()

    products_df = products_df.rename(
        columns={
            "order_item_id": "Item #",
            "product_id": "Product ID",
            "product_category_name_english": "Category",
            "price": "Price (R$)",
            "freight_value": "Freight (R$)",
            "seller_id": "Seller ID",
        }
    )

    products_df["Category"] = products_df["Category"].fillna(
        "Unknown"
    )

    st.dataframe(
        products_df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # SELLERS
    # --------------------------------------------------------

    st.subheader("🏪 Seller Details")

    sellers_df = order_details[
        [
            "seller_id",
            "seller_city",
            "seller_state",
        ]
    ].drop_duplicates().rename(
        columns={
            "seller_id": "Seller ID",
            "seller_city": "City",
            "seller_state": "State",
        }
    )

    st.dataframe(
        sellers_df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    st.subheader("💳 Payment Details")

    payment_df = order_details[
        [
            "payment_type",
            "payment_installments",
            "payment_value",
        ]
    ].drop_duplicates().rename(
        columns={
            "payment_type": "Payment Type",
            "payment_installments": "Installments",
            "payment_value": "Payment Value (R$)",
        }
    )

    st.dataframe(
        payment_df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # REVIEW
    # --------------------------------------------------------

    st.subheader("⭐ Review Details")

    review_df = order_details[
        [
            "review_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
        ]
    ].drop_duplicates(
        subset=["review_id"]
    )

    review_df = review_df[
        review_df["review_id"].notna()
    ].rename(
        columns={
            "review_id": "Review ID",
            "review_score": "Score",
            "review_comment_title": "Review Title",
            "review_comment_message": "Review Comment",
        }
    )

    if review_df.empty:
        st.info("No review was recorded for this order.")
    else:
        st.dataframe(
            review_df,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # DELIVERY TIMELINE
    # --------------------------------------------------------

    st.subheader("🚚 Order Timeline")

    timeline = pd.DataFrame([
        {
            "Stage": "Purchased",
            "Date": first["order_purchase_timestamp"],
        },
        {
            "Stage": "Approved",
            "Date": first["order_approved_at"],
        },
        {
            "Stage": "Carrier",
            "Date": first["order_delivered_carrier_date"],
        },
        {
            "Stage": "Delivered",
            "Date": first["order_delivered_customer_date"],
        },
        {
            "Stage": "Estimated",
            "Date": first["order_estimated_delivery_date"],
        },
    ])

    timeline["Date"] = pd.to_datetime(
        timeline["Date"],
        errors="coerce",
    )

    timeline = timeline.dropna(subset=["Date"])

    if not timeline.empty:

        fig = px.scatter(
            timeline,
            x="Date",
            y="Stage",
            text="Stage",
            title="Order Fulfillment Timeline",
        )

        fig.update_traces(marker_size=12)

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# ============================================================
# CUSTOMER SPEND
# ============================================================

st.divider()
st.subheader("📈 Customer Spend Over Time")

spend_data = orders.copy()
spend_data["order_date"] = pd.to_datetime(
    spend_data["order_date"]
)

fig = px.line(
    spend_data.sort_values("order_date"),
    x="order_date",
    y="payment_value",
    markers=True,
    title="Customer Order Value Over Time",
)

fig.update_layout(
    xaxis_title="Order Date",
    yaxis_title="Payment Value (R$)",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

st.divider()

st.caption(
    "Customer 360 Analytics Platform • "
    "Customer → Order → Product → Seller → Payment → Review"
)
