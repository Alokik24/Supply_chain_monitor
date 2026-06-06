# Supply Chain Anomaly Monitor

A real-time data engineering and machine learning pipeline designed to ingest manufacturing sensor data, identify operational anomalies, and deploy an AI investigation agent to diagnose root causes.

## The System Architecture

This project is split into two primary data paths:
1. **The Hot Path (Real-Time):** Ingests incoming sensor data, validates payloads via FastAPI, and updates in-memory features using Redis for instant visibility.
2. **The Cold Path (Asynchronous):** Appends raw records to PostgreSQL for historical logging, evaluates data using a Scikit-learn model, and triggers a LangChain Agent to write root-cause summaries.

## Project Structure

```text
supply_chain_monitor/
├── data/               # Scripts to generate synthetic datasets
├── db/                 # Database schemas and historical migrations
├── docs/               # System architecture registry documents
├── src/                # Core application source code
└── tests/              # Python testing suites (pytest)
```