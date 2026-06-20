# Supply Chain Anomaly Monitor

## Overview
Real-time telemetry ingestion platform for manufacturing systems, built with FastAPI, PostgreSQL, Redis and asynchronous event processing.

The platform ingests high-volume sensor telemetry, enforces idempotent writes, stores normalized event records, and provides the foundation for anomaly detection and automated investigations.

## Current System Architecture

The framework splits operations into two parallel runtime channels to maximize write throughput while ensuring transactional state consistency:

1. **The Hot Path (Real-Time):** Ingests incoming sensor telemetry packets, validates incoming structural payloads via FastAPI, and tracks sliding time-window metrics inside Redis for sub-millisecond operational visibility.
2. **The Cold Path (Asynchronous):** Appends raw records directly into PostgreSQL for immutable storage, processes batches using Scikit-learn models, and leverages an LLM-powered LangChain Agent to append structured root-cause findings.

```
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
 ```

### Planned Future pipeline
```
sensor_readings
      ↓
Feature Store
      ↓
Anomaly Detection
      ↓
anomaly_cases
      ↓
Evidence Engine
```

## Implemented Features
```
 Dockerized infrastructure
 FastAPI ingestion service
 PostgreSQL persistence layer
 Redis integration
 Idempotent ingestion
 Async replay engine
 Integration tests
 Synthetic telemetry generation
 Health monitoring endpoints
```

## Synthetic Data Model

The project uses a deterministic synthetic telemetry generator simulating a manufacturing bottling line over 90 days of operation.

The simulator produces three synchronized sensor streams:

- Torque
- Conveyor Speed
- Fill Level

and injects a correlated Mechanical Conveyor Jam failure profile used for anomaly detection benchmarking.

Detailed mathematical definitions, anomaly injection mechanics, and simulation assumptions are documented in:

- ADR-02: Data Generation Strategy & Mathematical Profiles
- ADR-04: Synthetic Data Limitations & Assumptions

## Prerequisites

Install the following before running the project:

* Python 3.13+
* Docker Engine
* Docker Compose

Verify installation:

```bash
docker --version
docker compose version
python --version
```

## Project Directory Map

```text
supply_chain_monitor/
├── data/               # Scripts to generate deterministic synthetic datasets
│   ├── generate.py     # Deterministic 3-sensor wide-format generation script
│   └── sensor_data.csv # Raw wide hardware dataset file (Blocked by .gitignore)
├── db/                 # Relational database tier configuration
│   └── migrations/     # Versioned SQL migration files (001_init_schema.sql)
├── docs/               # System architecture registry documents
│   └── architecture/   # Structural trade-off logs, ADRs, and Git developer manuals
├── src/                # Production application source code
│   ├── seed_db.py      # Database initialization & data seeding
│   ├── features.py     # 30-minute rolling feature engineering pipeline
│   ├── train.py        # Model training & evaluation (RF + Isolation Forest)
│   ├── main.py         # FastAPI application server
│   └── db.py           # PostgreSQL & Redis connection configuration
├── tests/              # Automated verification suites (pytest)
└── models/             # Trained scikit-learn model artifacts (gitignored)
```

## Complete Workflow Reference

| Step | Command | Output | Purpose |
|:---|:---|:---|:---|
| **1. Setup** | `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt` | Virtual environment with dependencies | Isolate Python packages |
| **2. Generate Data** | `python3 data/generate.py` | `data/sensor_data.csv` (129,600 rows) | Create synthetic 90-day telemetry |
| **3. Start Infrastructure** | `docker compose up -d` | PostgreSQL, Redis, FastAPI running | Initialize cloud infrastructure |
| **4. Seed Database** | `docker compose exec web python3 -m src.seed_db` | 3,000 sensor readings in PostgreSQL | Load initial data into DB |
| **5. Build Features** | `from src.features import build_feature_matrix` | 15 engineered features per sample | Transform raw telemetry into ML-ready vectors |
| **6. Train Models** | `python3 -c "from src.train import train_and_evaluate; train_and_evaluate('data/sensor_data.csv')"` | Models saved to `models/` + `metrics.json` | Train Random Forest & Isolation Forest |
| **7. Run Tests** | `pytest tests/` | 11 passed, 1 skipped | Validate feature engineering & models |
| **8. Check Health** | `curl http://localhost:8000/` | API + Redis + PostgreSQL status | Verify all services operational |
| **9. Cleanup** | `docker compose down --volumes` | Containers & volumes removed | Stop all infrastructure |

## Environment Verification & Execution

### 1. Initialize Virtual Environment Isolation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Deterministic Telemetry Generation

```bash
python3 data/generate.py
```

## Local Setup & Operations

### Start Infrastructure

```bash
docker compose up -d
```

This provisions:
* FastAPI (port 8000)
* PostgreSQL (port 5432)
* Redis (port 6379)

### Seed the Database

First, ensure the synthetic dataset exists:

```bash
python3 data/generate.py
```

Then, populate PostgreSQL (run inside the web container):

```bash
docker compose exec web python3 -m src.seed_db
```
### Run Automated Tests

```bash
pytest tests/
```

Expected result: **11 passed, 1 skipped** (health test requires Docker services)

To run health test inside Docker:

```bash
docker compose exec web pytest tests/test_health.py -v
```

## Feature Engineering Pipeline

Raw telemetry is transformed into machine-learning-ready feature vectors using rolling statistical analysis.

Implemented feature categories include:

- Rolling statistics
- Z-score normalization
- Rate-of-change metrics
- Baseline deviation measurements

The feature engineering layer is implemented in:

```python
src/features.py
```

For detailed feature-engineering rationale, temporal validation methodology, and evaluation design, see:

- ADR-03: Model Evaluation Framework
- ADR-05: Telemetry Representation Strategy & Relational Schema Design

## Model Training & Validation

The `src/train.py` module executes a strict chronological split and trains two anomaly detection models:

### Training Workflow

```python
from src.train import train_and_evaluate

train_and_evaluate(
    csv_path="data/sensor_data.csv",
    output_model_dir="models",
    metrics_path="metrics.json"
)
```

**Training Steps:**
1. **Load Raw Data:** Read wide-format CSV (129,600 records with 3 sensors + anomaly label)
2. **Chronological Split:** 80% training / 20% test (preserves temporal order to prevent data leakage)
3. **Feature Engineering:** Independently compute rolling features for train & test splits
4. **Model Fitting:**
   - **Isolation Forest:** Unsupervised anomaly detection (uses features only, no labels during training)
   - **Random Forest Classifier:** Supervised binary classification (uses both features and `is_anomaly` labels)
5. **Evaluation:** Compute precision, recall, F1, and confusion matrices on holdout test set
6. **Model Persistence:** Save trained models to `models/` directory; write metrics to `metrics.json`

**Running Training (local or Docker):**

```bash
# Local environment
cd /path/to/project && source venv/bin/activate
python3 -c "from src.train import train_and_evaluate; train_and_evaluate('data/sensor_data.csv')"

# Inside Docker container
docker compose exec web python3 -c "from src.train import train_and_evaluate; train_and_evaluate('data/sensor_data.csv')"
```

Models are saved to:
models/

Evaluation metrics are written to:
metrics.json

### Stop Infrastructure

```bash
docker compose down
```

To also remove persisted data volumes:

```bash
docker compose down --volumes
```

## Health Verification

The API exposes a health endpoint that validates connectivity to all backing services.

```bash
curl http://localhost:8000/
```

Expected response:

```json
{
  "api_status": "Live-Reload Activated",
  "redis_cache": "Connected",
  "postgres_db": "Connected"
}
```

## Model Performance Metrics

The machine learning pipeline trains two anomaly detection models on the synthetic telemetry dataset. Current trained model performance:

### Random Forest Classifier (Champion Model)
* **Precision:** 0.9696 (96.96% of predicted anomalies are correct)
* **Recall:** 0.9265 (92.65% of actual anomalies are detected)
* **F1 Score:** 0.9476
* **Confusion Matrix:**
  - True Negatives: 24,575
  - False Positives: 38
  - False Negatives: 96
  - True Positives: 1,211

### Isolation Forest (Baseline)
* **Precision:** 0.7964
* **Recall:** 0.7751
* **F1 Score:** 0.7856
* **Confusion Matrix:**
  - True Negatives: 24,354
  - False Positives: 259
  - False Negatives: 294
  - True Positives: 1,013

The **Random Forest** achieves significantly higher precision and recall, making it the production-deployed champion model.

## Development Infrastructure

The project is fully containerized using Docker Compose and validated through GitHub Actions.

The local runtime stack consists of:

* FastAPI
* PostgreSQL
* Redis

Every push and pull request triggers automated linting, database initialization, data seeding, and test execution.

## Architecture Decision Records

Detailed architectural trade-offs and engineering decisions are documented in the ADR registry.

| ADR | Description |
|------|-------------|
| ADR-01 | Storage & Ingestion Baseline Selection |
| ADR-02 | Data Generation Strategy & Mathematical Profiles |
| ADR-03 | Model Evaluation Framework |
| ADR-04 | Synthetic Data Limitations & Assumptions |
| ADR-05 | Telemetry Representation Strategy & Relational Schema Design |
| ADR-06 | Dataset Audit & Evaluation Validation |

These documents capture the rationale behind database design, feature engineering, model evaluation, telemetry representation, and benchmarking decisions.