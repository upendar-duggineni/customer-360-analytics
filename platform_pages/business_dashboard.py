"""Customer 360 analytics dashboard for the active business workspace."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.business_storage import initialize_storage, load_workspace_datasets
from src.business_analytics import build_customer_360

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

with st.sidebar:
    st.subheader("Analytics settings")
    churn_days = st.number_input("Inactivity threshold (days)", min_value=30, max_value=365, value=90, step=15)
    st.caption("Used for a transparent inactivity flag, not a predictive churn model.")

analytics = build_customer_360(tables, churn_days=int(churn_days))
summary = analytics["summary"]
if not summary:
    st.warning("Customer analytics could not be calculated from the saved datasets.")
    for note in analytics["limitations"]:
        st.write("• " + note)
    st.page_link("platform_pages/business_workspace.py", label="Review uploaded datasets", icon=":material/upload_file:")
    st.stop()

st.subheader("Business overview")
a, b, c, d = st.columns(4)
a.metric("Customers", f"{summary['customers']:,}")
b.metric("Orders", f"{summary['orders']:,}")
c.metric("Repeat purchase rate", f"{summary['repeat_rate']:.1%}" if pd.notna(summary["repeat_rate"]) else "Not available")
d.metric("Observed revenue", f"{summary['revenue']:,.2f}" if pd.notna(summary["revenue"]) else "Not available")
if summary["revenue_source"]:
    st.caption(f"Revenue source: {summary['revenue_source']} · Currency is not inferred.")
st.caption(f"Data snapshot: {summary['snapshot_date'].date()} · Inactivity rule: more than {summary['churn_days']} days since last recorded order.")

for limitation in analytics["limitations"]:
    st.info(limitation)

tabs = st.tabs(["Executive insights", "RFM segmentation", "Retention & cohorts", "Customer explorer", "Saved datasets"])

with tabs[0]:
    st.subheader("Business insights")
    if analytics["insights"]:
        for insight in analytics["insights"]:
            st.markdown(f"- {insight}")
    else:
        st.caption("More complete datasets will unlock additional insights.")

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

with tabs[1]:
    st.subheader("RFM customer segmentation")
    rfm = analytics["rfm"]
    if "segment" not in rfm:
        st.info("RFM requires valid order dates and a supported revenue field.")
    else:
        segment_counts = rfm["segment"].value_counts().rename_axis("segment").reset_index(name="customers")
        left, right = st.columns([1, 2])
        left.plotly_chart(px.pie(segment_counts, names="segment", values="customers", hole=0.55, title="Customer segments"), use_container_width=True)
        right.plotly_chart(px.bar(segment_counts, x="segment", y="customers", title="Customers by RFM segment"), use_container_width=True)
        st.dataframe(rfm.sort_values("RFM_score", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("Download RFM segmentation CSV", rfm.to_csv(index=False).encode("utf-8"), "customer_rfm_segmentation.csv", "text/csv")

with tabs[2]:
    st.subheader("Repeat purchase and retention")
    repeat = summary["repeat_rate"]
    st.metric("Customers with more than one order", f"{summary['repeat_customers']:,}")
    st.metric("Repeat purchase rate", f"{repeat:.1%}" if pd.notna(repeat) else "Not available")
    cohort = analytics["cohort"]
    if cohort.empty:
        st.info("Cohort retention requires valid order dates.")
    else:
        fig = go.Figure(data=go.Heatmap(
            z=cohort.to_numpy(dtype=float),
            x=[f"Month {int(x)}" for x in cohort.columns],
            y=cohort.index.tolist(),
            colorscale="Blues",
            zmin=0,
            zmax=1,
            colorbar={"title": "Retention"},
            hovertemplate="Cohort: %{y}<br>%{x}<br>Retention: %{z:.1%}<extra></extra>",
        ))
        fig.update_layout(title="Customer cohort retention", xaxis_title="Months since first purchase", yaxis_title="First purchase cohort")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Each cell is the share of a cohort with at least one order in that calendar month. Later cohorts have fewer observed months.")

with tabs[3]:
    st.subheader("Customer 360 explorer")
    customer_frame = analytics["customers"]
    if customer_frame.empty:
        st.info("No customer-level results available.")
    else:
        search = st.text_input("Search customer ID")
        view = customer_frame
        if search:
            view = view[view["customer_id"].astype(str).str.contains(search, case=False, na=False)]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("Download Customer 360 results CSV", customer_frame.to_csv(index=False).encode("utf-8"), "customer_360_results.csv", "text/csv")

with tabs[4]:
    st.subheader("Saved datasets and exports")
    for name, frame in tables.items():
        with st.expander(f"{name} · {len(frame):,} rows"):
            st.caption(f"Source: {metadata[name]['filename']} · Last saved: {metadata[name]['updated_at']}")
            st.dataframe(frame.head(100), use_container_width=True, hide_index=True)
            st.download_button(f"Download {name} as CSV", frame.to_csv(index=False).encode("utf-8"),
                               file_name=f"{name.lower().replace(' ', '_')}_normalized.csv", mime="text/csv", key=f"download_{name}")
    st.download_button("Download full Customer 360 results", analytics["customers"].to_csv(index=False).encode("utf-8"), "customer_360_results.csv", "text/csv")

st.page_link("platform_pages/business_workspace.py", label="Manage workspace and datasets", icon=":material/settings:")
st.warning("RFM and retention are descriptive analytics. The inactivity flag is a configurable rule, not a machine-learning churn prediction. Observed customer revenue is historical, not predictive lifetime value. Workspace access still uses a shared key; individual accounts and role-based access are future work.")
