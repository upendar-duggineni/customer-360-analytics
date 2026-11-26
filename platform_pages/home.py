"""Public landing page for the Customer 360 platform."""
import streamlit as st


st.markdown(
    """
    <style>
    .hero {
        padding: 2.2rem 0 1.3rem 0;
    }
    .eyebrow {
        color: #0E7C66;
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .hero-copy {
        color: #667085;
        font-size: 1.08rem;
        max-width: 780px;
        line-height: 1.65;
    }
    .choice-card {
        min-height: 255px;
        padding: 1.35rem;
        border: 1px solid rgba(128, 128, 128, .25);
        border-radius: 16px;
        background: var(--secondary-background-color);
    }
    .choice-icon {
        font-size: 2rem;
        margin-bottom: .5rem;
    }
    .choice-card p {
        color: var(--text-color);
        opacity: .78;
        line-height: 1.55;
    }
    .subtle {
        color: #667085;
        font-size: .9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Customer intelligence · Business analytics</div>
      <h1 style="font-size:2.65rem; line-height:1.15; margin:.55rem 0;">
        Know your customers.<br>Grow with better decisions.
      </h1>
      <p class="hero-copy">
        Explore a complete Customer 360 analytics demonstration using the
        Olist public dataset, or discover how your own business data will
        power customer, sales and retention insights.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

demo_col, business_col = st.columns(2, gap="large")

with demo_col:
    st.markdown(
        """
        <div class="choice-card">
          <div class="choice-icon">📊</div>
          <h3>Explore the Customer 360 demo</h3>
          <p>
            Explore the existing analytics experience using the public
            Brazilian Olist e-commerce dataset. Review executive KPIs,
            customer segments, sales, products, payments and delivery.
          </p>
          <span class="subtle">No account or upload required · Sample data</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "dashboard/app.py",
        label="Explore Olist demo",
        icon=":material/arrow_forward:",
        width="stretch",
    )

with business_col:
    st.markdown(
        """
        <div class="choice-card">
          <div class="choice-icon">🏢</div>
          <h3>Analyze my business</h3>
          <p>
            A separate workspace for business owners, analysts and teams.
            The planned onboarding flow will accept company data and turn
            it into customer, revenue and retention intelligence.
          </p>
          <span class="subtle">Bring your own data · Business workspace</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        "platform_pages/business_workspace.py",
        label="Open business workspace",
        icon=":material/arrow_forward:",
        width="stretch",
    )

st.divider()

st.subheader("One platform. Two ways to get value.")

feature_cols = st.columns(4)
features = [
    ("👥", "Customer intelligence", "Understand customer value and purchasing behaviour."),
    ("🎯", "Segmentation", "Group customers using meaningful behavioural signals."),
    ("🔁", "Retention analytics", "Explore repeat purchasing and customer activity."),
    ("📈", "Business performance", "Connect customer behaviour with sales outcomes."),
]
for col, (icon, title, description) in zip(feature_cols, features):
    with col:
        st.markdown(f"### {icon} {title}")
        st.caption(description)

st.caption(
    "Demo data is sourced from the public Olist Brazilian E-Commerce dataset. "
    "Business data onboarding, account management and integrations are under development."
)
