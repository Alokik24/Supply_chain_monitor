import streamlit as st

st.title("🏗️ Architecture & Design")

st.markdown("""
LineGuard simulates a real-world manufacturing monitoring system.

Instead of physical IoT devices, a synthetic telemetry dataset is replayed through a complete ingestion, scoring, and incident management pipeline.

The goal is to demonstrate how production telemetry can be transformed into actionable investigation cases for factory operators.
""")

st.header("System Overview")

st.markdown("""
```text
Factory Telemetry
        ↓
Telemetry Streamer
        ↓
FastAPI Ingestion
        ↓
PostgreSQL Storage
        ↓
Feature Engineering
        ↓
ML Scoring Worker
        ↓
Incident Creation
        ↓
Operator Dashboard""")

st.divider()

st.header("Core Components")

c1, c2, c3 = st.columns(3)

with c1:
    st.info("""
    PostgreSQL

    Stores:
    • Raw telemetry
    • Incident cases
    • Investigation records
    """)

with c2:
    st.info("""
    Redis

    Stores:
    • Worker watermarks
    • Cached features
    • Fast state access
    """)

with c3:
    st.info("""
    ML Worker

    Performs:
    • Feature generation
    • Model inference
    • Case creation
    """)

st.divider()

st.header("Dataset")

m1, m2, m3 = st.columns(3)

m1.metric("Duration", "90 Days")
m2.metric("Rows", "129,600")
m3.metric("Injected Anomalies", "~5%")

st.caption(
    "The dataset simulates conveyor telemetry using torque, conveyor speed, and fill-level sensors."
)

st.divider()

st.header("Design Decisions")

st.markdown("""
Why PostgreSQL?

Provides durable storage for telemetry and investigation workflows.

Why Redis?

Tracks worker progress and stores frequently accessed operational features.

Why a Background Worker?

Separates ingestion from machine-learning scoring so incoming telemetry is never blocked by model execution.
""")

st.divider()

st.header("Future Roadmap")

st.markdown("""
```
AI-assisted investigation agent
Root cause analysis workflows
Session-isolated demo environments
Multi-line factory support
Advanced telemetry visualizations
""")

st.divider()

st.header("Project Resources")

c1, c2, c3 = st.columns(3)

with c1:
    st.link_button(
        "GitHub Repository", "https://github.com/Alokik24/Supply_chain_monitor"
    )

with c2:
    st.link_button(
        "Architecture Diagrams", "https://github.com/YOUR_REPO/tree/main/docs"
    )

with c3:
    st.link_button(
        "ADRs & Documentation",
        "https://github.com/Alokik24/Supply_chain_monitor/tree/main/docs",
    )
