"""Customer 360 Analytics Platform entry point.

Run with:
    streamlit run platform_app.py

The existing Olist dashboard remains available as a separate page.
"""
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Customer 360 Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

home_page = st.Page(
    str(ROOT / "platform_pages" / "home.py"),
    title="Home",
    icon=":material/home:",
    url_path="home",
    default=True,
)

demo_page = st.Page(
    str(ROOT / "dashboard" / "app.py"),
    title="Explore Olist Demo",
    icon=":material/monitoring:",
    url_path="demo",
)

customer_explorer_page = st.Page(
    str(ROOT / "dashboard" / "pages" / "customer_details_fixed.py"),
    title="Customer 360 Explorer",
    icon=":material/person_search:",
    url_path="customer-explorer",
)

business_page = st.Page(
    str(ROOT / "platform_pages" / "business_workspace.py"),
    title="Analyze My Business",
    icon=":material/business:",
    url_path="business",
)

navigation = st.navigation(
    {
        "Platform": [home_page],
        "Explore the demo": [demo_page, customer_explorer_page],
        "Business analytics": [business_page],
    },
    position="top",
)

navigation.run()
