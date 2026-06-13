# Supply Chain Anomaly Monitor

A real-time data engineering and machine learning pipeline designed to ingest manufacturing sensor data, identify operational anomalies, and deploy an AI investigation agent to diagnose root causes.

## The System Architecture

The framework splits operations into two parallel runtime channels to maximize write throughput while ensuring transactional state consistency:

1. **The Hot Path (Real-Time):** Ingests incoming sensor telemetry packets, validates incoming structural payloads via FastAPI, and tracks sliding time-window metrics inside Redis for sub-millisecond operational visibility.
2. **The Cold Path (Asynchronous):** Appends raw records directly into PostgreSQL for immutable storage, processes batches using Scikit-learn models, and leverages an LLM-powered LangChain Agent to append structured root-cause findings.

## Operational Truth Boundaries

The synthetic data generator simulates a Programmable Logic Controller (PLC) tracking a bottling line over **90 days of continuous operations** (129,600 elapsed baseline minutes). Telemetry is captured across **three distinct line metrics**:

* **Torque ($T$):** Measures motor rotational force. Baseline of $150\text{ Nm}$ with ambient Gaussian noise $\sigma = 18$.
* **Conveyor Speed ($S$):** Measures belt velocity. Baseline of $1200\text{ RPM}$, modulated by a cyclic daily sine wave ($\pm 10\text{ RPM}$) for temperature shifts, with an ambient noise profile $\sigma = 75$.
* **Fill Level ($F$):** Measures container liquid volume. Baseline of $80%$ volume with stable noise variance $\sigma = 9$.

### Correlated Failure Mode: Mechanical Conveyor Jam

Anomalies comprise **strictly 5%** of total system runtime and simulate a physical line jam where all three attributes break operational limits simultaneously:

* **Torque Reaction:** Sudden positive uniform spike ($+50\text{ Nm}$ to $+100\text{ Nm}$) as the motor strains against physical friction.
* **Speed Reaction:** Catastrophic negative uniform drop ($-300\text{ RPM}$ to $-500\text{ RPM}$) as the line grinds to a halt.
* **Fill Level Reaction:** Severe drop ($-20%$ to $-40%$) as bottle misalignments under the filling nozzles cause liquid spillage and underfills.

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
│   ├── generate.py     # Synthetic telemetry data generator
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

### 3. Verify Baseline Matrix Integrity

```bash
python3 -c "import pandas as pd; df = pd.read_csv('data/sensor_data.csv'); print(df.groupby('is_anomaly').mean())"
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

**Expected output:**
```
Connecting to infrastructure pool at: postgresql://postgres:****@database:5432/supply_chain_telemetry
Reading and applying migration: 001_init_schema.sql...
Schema tables successfully verified/created.
Processing hardware log matrix (unrolling wide-to-narrow conversion)...
Staging database transaction: committing 3000 narrow entries...
Success! Relational database populated with 1000 wide events (3000 rows).

==================================================
DATABASE SEED VERIFICATION METRICS:
==================================================
 Sensor Type: fill_level      | Rows Inserted: 1000  | Calculated Mean: 77.86
 Sensor Type: torque          | Rows Inserted: 1000  | Calculated Mean: 157.73
 Sensor Type: conveyor_speed  | Rows Inserted: 1000  | Calculated Mean: 1163.94
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

The `src/features.py` module transforms raw sensor telemetry into machine-learning-ready feature vectors using a 30-minute rolling window computation:

### Feature Extraction Workflow

1. **Narrow-to-Wide Transformation:** Converts database entity-attribute-value (EAV) rows back into a wide matrix format (timestamp, line_id, torque, conveyor_speed, fill_level)
2. **Rolling Statistics:** Computes 30-minute sliding window means and standard deviations per sensor per production line
3. **Normalized Scoring:** Calculates Z-scores to capture deviation from baseline (mean = 0, std = 1)
4. **Rate of Change:** Tracks first-order derivatives to detect sudden velocity shifts
5. **Baseline Delta:** Measures divergence from global operational averages

**Key Features Extracted (15 total):**
- Per-sensor rolling standard deviation
- Per-sensor Z-score
- Per-sensor rate of change
- Per-sensor delta from baseline

```python
from src.features import build_feature_matrix, SENSOR_TYPES
feature_matrix = build_feature_matrix(df_narrow)  # Returns DataFrame with 15 engineered features
```

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

**Training Output:**

```
Engineering features independently for train split...
Engineering features independently for test split...

========== ISOLATION FOREST EVALUATION ==========
Precision:  0.7964
Recall:     0.7751
F1 Score:   0.7856

========== RANDOM FOREST EVALUATION ==========
Precision:  0.9696
Recall:     0.9265
F1 Score:   0.9476

Champion Model: random_forest
Models saved to: models/
Metrics written to: metrics.json
```

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

## Architecture Documentation

Detailed design decisions are maintained in the Architecture Decision Record (ADR) registry:

```text
docs/architecture/
├── ARCH-01
├── ARCH-02
├── ARCH-03
├── ARCH-04
└── ARCH-05
```
