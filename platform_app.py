"""Customer 360 Analytics Platform entry point."""
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Customer 360 Analytics Platform", page_icon="📊", layout="wide")

home = st.Page(str(ROOT / "platform_pages/home.py"), title="Home", icon=":material/home:", default=True)
demo = st.Page(str(ROOT / "dashboard/app.py"), title="Explore Olist Demo", icon=":material/monitoring:")
explorer = st.Page(str(ROOT / "dashboard/pages/customer_details_fixed.py"), title="Customer 360 Explorer", icon=":material/person_search:")
upload = st.Page(str(ROOT / "platform_pages/business_workspace.py"), title="Upload Business Data", icon=":material/upload_file:")
business_dashboard = st.Page(str(ROOT / "platform_pages/business_dashboard.py"), title="My Business Dashboard", icon=":material/analytics:")

st.navigation({
    "Platform": [home],
    "Explore the demo": [demo, explorer],
    "Business analytics": [upload, business_dashboard],
}, position="top").run()
