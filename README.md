# Supply Chain Anomaly Monitor

## Overview

Real-time telemetry ingestion platform for manufacturing systems built with FastAPI, PostgreSQL, Redis, and asynchronous event processing.

The platform ingests high-volume sensor telemetry, enforces idempotent writes, stores normalized event records, and provides the foundation for anomaly detection workflows.

---

## Current System Architecture

```text
Synthetic Telemetry Generator
            │
            ▼
        CSV Dataset
            │
            ▼
   Async Replay Engine
            │
            ▼
        FastAPI API
            │
            ▼
   Pydantic Validation
            │
            ▼
  Idempotent Upsert Layer
            │
            ▼
       PostgreSQL
            │
            ▼
     Scoring Worker
            │
            ▼
   Feature Engineering
            │
            ▼
     ML Inference
            │
            ▼
     Anomaly Cases

```

### Planned Detection Pipeline

```text
sensor_readings
      ↓
Feature Engineering
      ↓
Random Forest / Isolation Forest
      ↓
anomaly_cases
      ↓
Operator Investigation Workflow
```

## Machine Learning Foundation

The project includes an offline anomaly-detection training pipeline built using engineered telemetry features.

Implemented models:

- Random Forest Classifier
- Isolation Forest

Model development, evaluation methodology, and validation strategy are documented in:

- ADR-03
- EDA_Technical_Report
- ADR-06

## Implemented Features

- Dockerized infrastructure
- FastAPI ingestion service
- PostgreSQL persistence layer
- Redis integration
- Idempotent ingestion
- Async replay engine
- Integration tests
- Synthetic telemetry generation
- Health monitoring endpoints
- Cold-path scoring worker
- Watermark-based incremental processing
- Redis feature caching
- Automated anomaly case creation
- Anomaly query API
- Incident lifecycle management

---

## Synthetic Data Model

The project uses a deterministic synthetic telemetry generator simulating a manufacturing bottling line over 90 days of operation.

Current simulated sensors:

- Torque
- Conveyor Speed
- Fill Level

For detailed mathematical definitions, anomaly injection logic, and simulation assumptions, see:

- ADR-02: Data Generation Strategy & Mathematical Profiles
- ADR-04: Synthetic Data Limitations & Assumptions

---

## Prerequisites

- Python 3.13+
- Docker Engine
- Docker Compose

---

## Project Directory Map

```text
supply_chain_anomaly_detection/
├── data/
├── db/
├── docs/
├── src/
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Quick Start

### Clone Repository

```bash
git clone <repository-url>
cd supply_chain_anomaly_detection
```

### Create Environment File

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=supply_chain_telemetry
POSTGRES_HOST=database
POSTGRES_PORT=5432
```

### Start Infrastructure

```bash
docker compose up -d --build
```

### Verify Service Health

```bash
curl http://localhost:8000/health
```

### Generate Telemetry

```bash
python data/generate.py
```

### Replay Telemetry

```bash
python data/stream_dataset.py
```

### Replay Verification

The telemetry replay engine was successfully executed against the live ingestion stack.

Execution summary:

- 129,600 wide telemetry rows processed
- 388,800 normalized sensor events generated
- Asynchronous HTTP ingestion through FastAPI
- PostgreSQL persistence validated
- Idempotent event handling verified

This replay exercise validated the complete ingestion workflow from dataset generation through database persistence.

### Run Tests

```bash
pytest tests/
```

---

## Database Schema

### sensor_readings

| Column | Type |
|----------|----------|
| id | BIGINT (automatically acting as BIGSERIAL) |
| line_id | VARCHAR(50) |
| sensor_type | VARCHAR(50) |
| value | DOUBLE PRECISION |
| timestamp | TIMESTAMP WITH TIME ZONE |

Design rationale and schema tradeoffs are documented in:

- ADR-05: Telemetry Representation Strategy & Relational Schema Design

### Persistence Verification

Example validation query:

```sql
SELECT *
FROM sensor_readings
ORDER BY id DESC
LIMIT 5;
```

The database was successfully populated through the replay engine and now serves as the primary telemetry event ledger.


## API Reference

### Health Check

```http
GET /health
```

### Sensor Ingestion

```http
POST /readings
```

### Anomaly Detection
```http
GET /anomalies
GET /anomalies/{id}
PATCH /anomalies/{id}
GET /anomalies/stats
GET /anomalies/worker-status
```
---

## Testing

The project includes integration tests covering:

- Request validation
- Database persistence
- Duplicate event handling
- Transaction isolation
- End-to-end ingestion behavior

Validation methodology and evaluation strategy are documented in:

- ADR-03: Model Evaluation Framework
- ADR-06: Dataset Audit & Evaluation Validation

---

## Current Project Status

| Component                    | Status      |
| ---------------------------- | ----------- |
| Docker Infrastructure        | Complete    |
| PostgreSQL Integration       | Complete    |
| Redis Integration            | Complete    |
| FastAPI Service              | Complete    |
| Telemetry Generation         | Complete    |
| Async Replay Engine          | Complete    |
| Idempotent Ingestion         | Complete    |
| Cold Path Scoring Worker     | Complete    |
| Feature Engineering Pipeline | Complete    |
| Anomaly Detection Service    | Complete    |
| Anomaly Case Creation        | Complete    |
| Investigation Workflow API   | Complete    |
| Dashboard UI                 | In Progress |
| Session Isolation            | Planned     |
| AI Investigation Agent       | Planned     |


---

## Architecture Decision Records

| ADR | Description |
|------|-------------|
| ADR-01 | Storage & Ingestion Baseline Selection |
| ADR-02 | Data Generation Strategy & Mathematical Profiles |
| ADR-03 | Model Evaluation Framework |
| ADR-04 | Synthetic Data Limitations & Assumptions |
| ADR-05 | Telemetry Representation Strategy & Relational Schema Design |
| ADR-06 | Dataset Audit & Evaluation Validation |
| ADR-07 | Hot Path Telemetry Ingestion Strategy
| ADR-08 | Cold Path Scoring Pipeline & Watermark-Based Processing