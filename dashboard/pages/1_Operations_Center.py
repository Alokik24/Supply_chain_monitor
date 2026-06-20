import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st_autorefresh(
    interval=5000,
    key="dashboard_refresh"
)

API_BASE = "http://localhost:8000"

st.title("⚙️ Operations Center")

st.warning("""
Demo Mode Active

Telemetry is replayed at an accelerated rate so anomaly detection,
incident creation, and investigation workflows can be observed
within a few minutes.
""")

try:

    stats = requests.get(
        f"{API_BASE}/anomalies/stats"
    ).json()

    worker = requests.get(
        f"{API_BASE}/anomalies/worker-status"
    ).json()

    anomalies = requests.get(
        f"{API_BASE}/anomalies"
    ).json()

except Exception as e:

    st.error(f"Unable to connect to backend API: {e}")
    st.stop()

df = pd.DataFrame(anomalies)

# --------------------------------------------------
# Metrics
# --------------------------------------------------

st.subheader("System Metrics")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Cases", stats["total_cases"])
c2.metric("Flagged", stats["flagged"])
c3.metric("Investigating", stats["investigating"])
c4.metric("Resolved", stats["resolved"])

st.divider()

# --------------------------------------------------
# Worker Status
# --------------------------------------------------

st.subheader("Worker Status")

if "last_watermark" not in st.session_state:
    st.session_state.last_watermark = worker["watermark"]

worker_col1, worker_col2 = st.columns(2)

if worker["watermark"] > st.session_state.last_watermark:
    worker_col1.success("Worker Active")
else:
    worker_col1.warning("No New Processing")

worker_col2.info(
    f"Watermark: {worker['watermark']}"
)

st.session_state.last_watermark = worker["watermark"]

st.divider()

# --------------------------------------------------
# Status Distribution
# --------------------------------------------------

st.subheader("Incident Distribution")

if not df.empty:

    status_counts = (
        df["status"]
        .value_counts()
    )

    st.bar_chart(status_counts)

st.divider()

# --------------------------------------------------
# Recent Incidents
# --------------------------------------------------

st.subheader("Recent Incidents")

recent_df = df.head(20)

st.dataframe(
    recent_df,
    use_container_width=True,
    height=350
)

st.divider()

# --------------------------------------------------
# Case Management
# --------------------------------------------------

st.subheader("Case Management")

if not df.empty:

    case_lookup = {
        f"Case #{row['id']} | {row['status']}":
        row["id"]
        for row in anomalies[:50]
    }

    selected = st.selectbox(
        "Select Incident",
        list(case_lookup.keys())
    )

    selected_id = case_lookup[selected]

    case = requests.get(
        f"{API_BASE}/anomalies/{selected_id}"
    ).json()

    left, right = st.columns([2, 1])

    with left:
        st.json(case)

    with right:

        new_status = st.selectbox(
            "Update Status",
            [
                "FLAGGED",
                "INVESTIGATING",
                "RESOLVED",
                "FALSE_POSITIVE"
            ]
        )

        if st.button(
            "Update Incident Status",
            use_container_width=True
        ):

            requests.patch(
                f"{API_BASE}/anomalies/{selected_id}",
                json={
                    "status": new_status
                }
            )

            st.success("Status Updated")
            st.rerun()