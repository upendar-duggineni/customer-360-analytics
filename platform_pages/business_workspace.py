"""Business workspace entry page.

This milestone introduces the business experience without collecting or
persisting company data. Secure onboarding and ingestion will be added
in subsequent milestones.
"""
import streamlit as st


st.title("🏢 Analyze my business")
st.caption(
    "A private analytics workspace for business owners, individual analysts "
    "and company teams."
)

st.info(
    "Business onboarding is under development. This page does not currently "
    "upload, store or process company files."
)

st.subheader("What the business workspace is being built to do")

steps = [
    (
        "1. Create a workspace",
        "Set up an individual workspace or a company workspace and invite team members.",
    ),
    (
        "2. Bring your business data",
        "Upload CSV or Excel files, or connect a supported e-commerce platform.",
    ),
    (
        "3. Map and validate your data",
        "Match your columns to the Customer 360 model and review data-quality checks before processing.",
    ),
    (
        "4. Explore your analytics",
        "View customer profiles, sales performance, RFM segments and retention insights based on your own data.",
    ),
]

for heading, description in steps:
    with st.container(border=True):
        st.markdown(f"#### {heading}")
        st.write(description)

st.subheader("Planned data sources")

source_cols = st.columns(4)
sources = [
    ("📄", "CSV files", "Initial file-import format"),
    ("📗", "Excel files", "Initial file-import format"),
    ("🛍️", "Shopify", "Planned direct integration"),
    ("🛒", "WooCommerce", "Planned direct integration"),
]
for col, (icon, name, status) in zip(source_cols, sources):
    with col:
        with st.container(border=True):
            st.markdown(f"### {icon}")
            st.markdown(f"**{name}**")
            st.caption(status)

st.warning(
    "Do not upload confidential or personal company data to this prototype. "
    "Authentication, workspace isolation, secure ingestion and access controls "
    "must be implemented and tested before real business data is accepted."
)

st.page_link(
    "platform_pages/home.py",
    label="Back to platform home",
    icon=":material/home:",
)
