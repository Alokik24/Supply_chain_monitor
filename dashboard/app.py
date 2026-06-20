import streamlit as st

st.set_page_config(
    page_title="LineGuard",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 LineGuard")
st.caption("Manufacturing Anomaly Detection & Investigation Platform")

st.markdown("""
### You are a factory operator.

Your conveyor line is monitored by three sensors:

⚙️ Torque • 🏃 Conveyor Speed • 📦 Fill Level

Most sensor fluctuations are normal.

The challenge is determining which patterns represent routine machine behaviour and which may indicate a developing production issue.

**LineGuard continuously evaluates telemetry and creates investigation cases when suspicious behaviour is detected.**
""")

st.divider()

c1, c2, c3 = st.columns(3)

with c1:
    st.info("""
    ⚙️ Torque

    Baseline:
    ~150 Nm

    Watch For:
    Unusual load increases
    """)

with c2:
    st.info("""
    🏃 Conveyor Speed

    Baseline:
    ~1200 RPM

    Watch For:
    Sustained slowdowns
    """)

with c3:
    st.info("""
    📦 Fill Level

    Baseline:
    ~80%

    Watch For:
    Underfill / Overfill
    """)

st.divider()

st.subheader("Explore LineGuard")

c1, c2 = st.columns(2)

with c1:
    st.success("""
    ⚙️ Operations Center

    Monitor active incidents,
    review anomaly cases,
    and update investigation status.
    """)

with c2:
    st.info("""
    🏗️ System Architecture

    Learn how telemetry flows through
    the ingestion, scoring, and
    incident management pipeline.
    """)

st.caption(
    "Use the sidebar to navigate between pages."
)