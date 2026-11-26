"""Adaptive Customer 360 analytics dashboard for the active business workspace."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.business_storage import initialize_storage, load_workspace_datasets
from src.business_analytics import build_customer_360
from src.customer_360_detail import build_customer_360_detail
from src.relationship_integrity import audit_relationships
from platform_pages.ai_assistant import render_ai_assistant


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

header_left, header_right = st.columns([8, 1.5], vertical_alignment="center")
header_left.title("📈 My Business Analytics Dashboard")
with header_right:
    render_ai_assistant(tables, workspace["workspace_id"])
st.caption(f"{workspace['workspace_name']} · {workspace['workspace_type']} · Persistent PostgreSQL data")
relationship_audit = audit_relationships(tables)
with st.expander("Dataset relationship integrity", expanded=relationship_audit["summary"]["relationships_needing_review"] > 0):
    audit_summary = relationship_audit["summary"]
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Relationships checked", audit_summary["relationships_checked"])
    rc2.metric("Healthy", audit_summary["healthy_relationships"])
    rc3.metric("Need review", audit_summary["relationships_needing_review"])
    rc4.metric("Unmatched rows", audit_summary["unmatched_source_rows"])
    st.caption("A match checks whether a source key exists in the target dataset. This audit does not delete, deduplicate or repair data.")
    st.dataframe(relationship_audit["relationships"], use_container_width=True, hide_index=True)
    for relationship, issue_frame in relationship_audit["issues"].items():
        if not issue_frame.empty:
            with st.expander(f"{relationship} · {len(issue_frame):,} issue rows"):
                st.dataframe(issue_frame, use_container_width=True, hide_index=True)
                st.download_button(
                    f"Download {relationship} issues",
                    issue_frame.to_csv(index=False).encode("utf-8"),
                    f"{relationship.lower().replace(' ', '_').replace('→', 'to')}_issues.csv",
                    "text/csv",
                    key=f"relationship_issue_{relationship}",
                )
if not tables:
    st.info("No saved datasets yet. Upload e-commerce data to get started.")
    st.page_link("platform_pages/business_workspace.py", label="Go to Data Translation Centre", icon=":material/upload_file:")
    st.stop()

with st.sidebar:
    st.subheader("Analytics settings")
    churn_days = st.number_input("Inactivity threshold (days)", min_value=30, max_value=365, value=90, step=15)
    st.caption("This is an inactivity rule, not a predictive churn model.")

analytics = build_customer_360(tables, churn_days=int(churn_days))
summary = analytics["summary"]
if summary.get("customer_only"):
    st.subheader("Customer profile overview")
    st.caption("Standalone customer analytics · Orders, Payments and Products are not required for this view.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unique customers", f"{summary['customers']:,}")
    c2.metric("Cities represented", f"{summary['cities']:,}" if summary["cities"] is not None else "Not mapped")
    c3.metric("Email coverage", f"{summary['email_coverage']:.1%}" if pd.notna(summary["email_coverage"]) else "Not mapped")
    c4.metric("Duplicate-ID rows", f"{summary['duplicate_customer_rows']:,}")
    quality = summary["data_quality"]
    st.subheader("Customer data quality")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Missing customer IDs", f"{quality['missing_customer_id_rows']:,}")
    q2.metric("Duplicate customer IDs", f"{quality['duplicate_customer_id_values']:,}")
    q3.metric("Invalid email rows", f"{quality['invalid_email_rows']:,}")
    q4.metric("Missing attribute rows", f"{quality['missing_attribute_rows']:,}")
    with st.expander("Review data quality issues", expanded=bool(quality['missing_customer_id_rows'] or quality['duplicate_customer_id_rows'] or quality['duplicate_email_values'] or quality['invalid_email_rows'] or quality['invalid_signup_date_rows'])):
        st.caption("These are review flags, not automatic deletions. All uploaded rows remain available in the explorer and original saved dataset.")
        st.json(quality)
        issue_rows = analytics["customers"]
        issue_filter = (
            issue_rows["data_quality_missing_id"]
            | issue_rows["data_quality_duplicate_id"]
            | issue_rows["data_quality_invalid_email"]
            | issue_rows["data_quality_duplicate_email"]
        )
        if "signup_date" in issue_rows:
            issue_filter |= issue_rows["signup_date"].isna()
        st.dataframe(issue_rows.loc[issue_filter], use_container_width=True, hide_index=True)
    with st.expander("Data coverage and limitations", expanded=True):
        for note in analytics["limitations"]:
            st.info(note)
    monthly = analytics["customer_profile"]["signup_monthly"]
    st.subheader("Customer acquisition")
    if not monthly.empty:
        st.plotly_chart(px.bar(monthly, x="month", y="new_customers", title="New customer registrations by month"), use_container_width=True)
    else:
        st.info("Map SignUpDate to signup_date to unlock customer acquisition trends.")
    st.subheader("Customer segmentation")
    st.caption("Segments are descriptive profile groups, not purchase-behaviour predictions. Segment counts use one representative record per valid customer ID.")
    segments = analytics["customer_segments"]
    seg_left, seg_right = st.columns(2)
    if not segments["signup_cohort"].empty:
        seg_left.plotly_chart(px.bar(segments["signup_cohort"], x="segment", y="customers", title="Customers by signup cohort"), use_container_width=True)
    else:
        seg_left.info("Signup cohorts require a mapped signup_date.")
    if not segments["profile_completeness"].empty:
        seg_right.plotly_chart(px.pie(segments["profile_completeness"], names="segment", values="customers", title="Profile completeness", hole=0.45), use_container_width=True)
    st.download_button("Download customer segment assignments", segments["assignments"].to_csv(index=False).encode("utf-8"), "customer_segments.csv", "text/csv")

    st.subheader("Customer geography")
    city, country = analytics["customer_profile"]["city"], analytics["customer_profile"]["country"]
    left, right = st.columns(2)
    if not city.empty:
        left.plotly_chart(px.bar(city.head(15), x="city", y="customers", title="Customers by city"), use_container_width=True)
    else:
        left.info("Map customer_city to view city distribution.")
    if not country.empty:
        right.plotly_chart(px.pie(country, names="country", values="customers", title="Customers by country", hole=0.45), use_container_width=True)
    else:
        right.info("Map customer_country to view country distribution.")
    st.subheader("Customer explorer")
    customer_frame = analytics["customers"]
    search = st.text_input("Search customer ID, name, email or city")
    view = customer_frame
    searchable = [col for col in ["customer_id", "customer_name", "customer_email", "customer_city", "customer_country"] if col in view]
    if search and searchable:
        mask = pd.Series(False, index=view.index)
        for col in searchable:
            mask |= view[col].astype("string").str.contains(search, case=False, na=False)
        view = view[mask]
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("Download customer profile CSV", customer_frame.to_csv(index=False).encode("utf-8"), "customer_profile_analytics.csv", "text/csv")
    st.subheader("Saved datasets")
    for name, frame in tables.items():
        with st.expander(f"{name} · {len(frame):,} rows"):
            st.caption(f"Source: {metadata[name]['filename']}")
            st.dataframe(frame.head(100), use_container_width=True, hide_index=True)
            st.download_button(f"Download {name} CSV", frame.to_csv(index=False).encode("utf-8"), f"{name.lower().replace(' ', '_')}.csv", "text/csv", key=f"customer_only_download_{name}")
    st.page_link("platform_pages/business_workspace.py", label="Manage workspace and upload more datasets", icon=":material/settings:")
    st.caption("Purchase frequency, repeat rate, RFM, cohorts, inactivity and revenue appear after compatible Orders and transaction datasets are uploaded.")
    st.stop()

if not summary:
    st.warning("Customer-level analytics are not available from the translated data.")
    for note in analytics["limitations"]:
        st.write("• " + note)
    st.page_link("platform_pages/business_workspace.py", label="Review translated data", icon=":material/upload_file:")
    st.stop()

st.subheader("Business overview")
a, b, c, d = st.columns(4)
a.metric("Customers", f"{summary['customers']:,}")
b.metric("Orders", f"{summary['orders']:,}")
c.metric("Repeat purchase rate", f"{summary['repeat_rate']:.1%}" if pd.notna(summary["repeat_rate"]) else "Not available")
d.metric("Observed revenue", f"{summary['revenue']:,.2f}" if pd.notna(summary["revenue"]) else "Not available")
if summary["revenue_source"]:
    st.caption(f"Revenue source: {summary['revenue_source']} · Currency is not inferred from the uploaded values.")
st.caption(f"Data snapshot: {summary['snapshot_date'].date()} · Inactivity threshold: {summary['churn_days']} days.")

if analytics["limitations"]:
    with st.expander("Data coverage and analytics limitations", expanded=True):
        for limitation in analytics["limitations"]:
            st.info(limitation)

# Build only tabs supported by the uploaded canonical datasets and data volume.
tab_names = ["Executive insights"]
if "segment" in analytics["rfm"].columns:
    tab_names.append("RFM segmentation")
if not analytics["cohort"].empty:
    tab_names.append("Retention & cohorts")
if not analytics["customers"].empty:
    tab_names.append("Customer explorer")
if not analytics["customers"].empty and {"Customers", "Orders"}.issubset(tables):
    tab_names.append("Customer 360")
if "Products" in tables or "Order items" in tables:
    tab_names.append("Product analytics")
if "Reviews" in tables:
    tab_names.append("Customer satisfaction")
if "Payments" in tables:
    tab_names.append("Payment analytics")
tab_names.append("Saved datasets")
tabs = st.tabs(tab_names)
tab_by_name = dict(zip(tab_names, tabs))

with tab_by_name["Executive insights"]:
    st.subheader("Evidence-based business insights")
    if analytics["insights"]:
        for insight in analytics["insights"]:
            st.markdown(f"- {insight}")
    else:
        st.caption("More complete transaction data will unlock additional insights.")
    monthly = analytics["monthly"]
    if not monthly.empty:
        st.subheader("Monthly business activity")
        metric_options = ["orders", "customers"]
        if "revenue" in monthly and monthly["revenue"].notna().any():
            metric_options.append("revenue")
        metric = st.selectbox("Trend metric", metric_options)
        st.plotly_chart(px.line(monthly, x="month", y=metric, markers=True, title=f"Monthly {metric.replace('_', ' ').title()}"), use_container_width=True)
    if "customer_state" in analytics["customers"]:
        geo = analytics["customers"].groupby("customer_state", dropna=False)["customer_id"].nunique().reset_index(name="customers")
        st.plotly_chart(px.bar(geo.sort_values("customers", ascending=False).head(15), x="customer_state", y="customers", title="Customers by state"), use_container_width=True)

if "RFM segmentation" in tab_by_name:
    with tab_by_name["RFM segmentation"]:
        rfm = analytics["rfm"]
        segment_counts = rfm["segment"].value_counts().rename_axis("segment").reset_index(name="customers")
        left, right = st.columns([1, 2])
        left.plotly_chart(px.pie(segment_counts, names="segment", values="customers", hole=0.55, title="Customer segments"), use_container_width=True)
        right.plotly_chart(px.bar(segment_counts, x="segment", y="customers", title="Customers by RFM segment"), use_container_width=True)
        st.dataframe(rfm.sort_values("RFM_score", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("Download RFM segmentation CSV", rfm.to_csv(index=False).encode("utf-8"), "customer_rfm_segmentation.csv", "text/csv")

if "Retention & cohorts" in tab_by_name:
    with tab_by_name["Retention & cohorts"]:
        st.subheader("Repeat purchase and cohort retention")
        st.metric("Customers with more than one order", f"{summary['repeat_customers']:,}")
        st.metric("Repeat purchase rate", f"{summary['repeat_rate']:.1%}" if pd.notna(summary["repeat_rate"]) else "Not available")
        cohort = analytics["cohort"]
        fig = go.Figure(data=go.Heatmap(
            z=cohort.to_numpy(dtype=float),
            x=[f"Month {int(x)}" for x in cohort.columns],
            y=cohort.index.tolist(),
            colorscale="Blues", zmin=0, zmax=1,
            colorbar={"title": "Retention"},
            hovertemplate="Cohort: %{y}<br>%{x}<br>Retention: %{z:.1%}<extra></extra>",
        ))
        fig.update_layout(title="Customer cohort retention", xaxis_title="Months since first purchase", yaxis_title="First purchase cohort")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Each cell is the share of a cohort with at least one order in that calendar month.")

if "Customer explorer" in tab_by_name:
    with tab_by_name["Customer explorer"]:
        customer_frame = analytics["customers"]
        search = st.text_input("Search customer identifier")
        view = customer_frame
        if search:
            view = view[view["customer_id"].astype(str).str.contains(search, case=False, na=False)]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("Download Customer 360 results CSV", customer_frame.to_csv(index=False).encode("utf-8"), "customer_360_results.csv", "text/csv")


if "Customer 360" in tab_by_name:
    with tab_by_name["Customer 360"]:
        st.subheader("Integrated Customer 360")
        st.caption("Select a customer to inspect their profile and related transactions. One-to-many datasets remain separate to avoid inflated joins.")
        customer_ids = (
            analytics["customers"]["customer_id"]
            .dropna().astype(str).str.strip().drop_duplicates().sort_values().tolist()
        )
        if not customer_ids:
            st.info("No valid customer identifiers are available for the explorer.")
        else:
            selected_customer = st.selectbox(
                "Select customer ID",
                customer_ids,
                key="integrated_customer_360_id",
            )
            detail = build_customer_360_detail(tables, selected_customer)
            detail_summary = detail["summary"]
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Orders", f"{detail_summary['orders']:,}")
            d2.metric("Order items", f"{detail_summary['order_items']:,}")
            d3.metric("Payments", f"{detail_summary['payments']:,}")
            d4.metric("Reviews", f"{detail_summary['reviews']:,}")
            if detail_summary["recorded_payment_total"] is not None:
                st.metric("Recorded payment total", f"{detail_summary['recorded_payment_total']:,.2f}")
                st.caption("Sum of recorded payment rows for this customer's orders; currency is not inferred.")
            if detail_summary["duplicate_product_keys_excluded"]:
                st.warning(
                    f"{detail_summary['duplicate_product_keys_excluded']:,} duplicate product keys were excluded from product enrichment. "
                    "Order-item rows are preserved and not multiplied."
                )
            for label, key in [
                ("Customer profile", "customer"),
                ("Orders", "orders"),
                ("Purchased items and matched product attributes", "order_items"),
                ("Payments", "payments"),
                ("Reviews", "reviews"),
            ]:
                frame = detail[key]
                with st.expander(f"{label} · {len(frame):,} rows", expanded=(key == "customer" or key == "orders")):
                    if frame.empty:
                        st.info("No related records are available for this customer in the uploaded datasets.")
                    else:
                        st.dataframe(frame.head(500), use_container_width=True, hide_index=True)
                        st.download_button(
                            f"Download {label.lower()} CSV",
                            frame.to_csv(index=False).encode("utf-8"),
                            f"customer_{selected_customer}_{key}.csv",
                            "text/csv",
                            key=f"customer_360_download_{key}",
                        )

if "Product analytics" in tab_by_name:
    with tab_by_name["Product analytics"]:
        products = tables.get("Products", pd.DataFrame())
        items = tables.get("Order items", pd.DataFrame())
        if "product_category" in products:
            counts = products["product_category"].fillna("Unknown").value_counts().head(20).rename_axis("category").reset_index(name="products")
            st.plotly_chart(px.bar(counts, x="category", y="products", title="Products by category"), use_container_width=True)
        elif "product_name" in products:
            st.dataframe(products[["product_id", "product_name"]].head(100), use_container_width=True)
        if not items.empty and "quantity" in items:
            qty = pd.to_numeric(items["quantity"], errors="coerce").sum()
            st.metric("Units sold in uploaded order lines", f"{qty:,.0f}")
        if products.empty and items.empty:
            st.info("No product data was found.")
        elif "product_id" not in items.columns and "product_id" not in products.columns:
            st.info("Map a product identifier to unlock product-level joins and deeper product analytics.")

if "Customer satisfaction" in tab_by_name:
    with tab_by_name["Customer satisfaction"]:
        reviews = tables["Reviews"]
        if "rating" in reviews:
            ratings = pd.to_numeric(reviews["rating"], errors="coerce").dropna()
            if not ratings.empty:
                st.metric("Average review rating", f"{ratings.mean():.2f}")
                distribution = ratings.value_counts().sort_index().rename_axis("rating").reset_index(name="reviews")
                st.plotly_chart(px.bar(distribution, x="rating", y="reviews", title="Review rating distribution"), use_container_width=True)
            else:
                st.info("Review records exist, but no numeric ratings were mapped.")
        else:
            st.info("Map a review rating field to enable satisfaction analytics.")

if "Payment analytics" in tab_by_name:
    with tab_by_name["Payment analytics"]:
        payments = tables["Payments"]
        amount_col = "payment_amount" if "payment_amount" in payments else "payment_value" if "payment_value" in payments else None
        if amount_col:
            values = pd.to_numeric(payments[amount_col], errors="coerce")
            st.metric("Recorded payment amount", f"{values.sum(min_count=1):,.2f}")
            if "payment_method" in payments:
                methods = payments.groupby("payment_method")[amount_col].sum().reset_index()
                st.plotly_chart(px.bar(methods, x="payment_method", y=amount_col, title="Payment value by method"), use_container_width=True)
        else:
            st.info("Map payment amount to enable payment analytics.")

with tab_by_name["Saved datasets"]:
    st.subheader("Canonical datasets and import reports")
    for name, frame in tables.items():
        with st.expander(f"{name} · {len(frame):,} rows"):
            st.caption(f"Source: {metadata[name]['filename']} · Last saved: {metadata[name]['updated_at']}")
            st.dataframe(frame.head(100), use_container_width=True, hide_index=True)
            st.download_button(f"Download {name} as CSV", frame.to_csv(index=False).encode("utf-8"),
                               file_name=f"{name.lower().replace(' ', '_')}.csv", mime="text/csv", key=f"download_{name}")
    st.download_button("Download full Customer 360 results", analytics["customers"].to_csv(index=False).encode("utf-8"), "customer_360_results.csv", "text/csv")

st.page_link("platform_pages/business_workspace.py", label="Manage workspace and datasets", icon=":material/settings:")
st.warning("RFM and cohorts are hidden below 30 orders. Inactivity is a configurable rule, not predictive churn. Observed customer revenue is historical, not predictive lifetime value. LLM mapping is not connected in this build.")
