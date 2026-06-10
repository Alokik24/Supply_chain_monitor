# Supply Chain Anomaly Monitor

A real-time data engineering and machine learning pipeline designed to ingest manufacturing sensor data, identify operational anomalies, and deploy an AI investigation agent to diagnose root causes.

## The System Architecture

The framework splits operations into two parallel runtime channels to maximize write throughput while ensuring transactional state consistency:

1. **The Hot Path (Real-Time):** Ingests incoming sensor telemetry packets, validates incoming structural payloads via FastAPI, and tracks sliding time-window metrics inside Redis for sub-millisecond operational visibility.
2. **The Cold Path (Asynchronous):** Appends raw records directly into PostgreSQL for immutable storage, processes batches using Scikit-learn models, and leverages an LLM-powered LangChain Agent to append structured root-cause findings.

## Operational Truth Boundaries

The synthetic data generator simulates a Programmable Logic Controller (PLC) tracking a bottling line over **90 days of continuous operations** (129,600 elapsed baseline minutes). Telemetry is captured across **three distinct line metrics**:

* **Torque ($T$):** Measures motor rotational force. Baseline of $150\text{ Nm}$ with ambient Gaussian noise $\sigma = 5$.
* **Conveyor Speed ($S$):** Measures belt velocity. Baseline of $1200\text{ RPM}$, modulated by a cyclic daily sine wave ($\pm 10\text{ RPM}$) for temperature shifts, with an ambient noise profile $\sigma = 2$.
* **Fill Level ($F$):** Measures container liquid volume. Baseline of $80%$ volume with stable noise variance $\sigma = 1$.

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
└── tests/              # Automated verification suites (pytest)
```

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

## Local Setup

### Create Environment Configuration

Create a `.env` file in the project root:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=my_ultra_secure_password_2026
POSTGRES_DB=supply_chain_telemetry
```

### Start Infrastructure

```bash
docker compose up --build -d
```

This provisions:

* FastAPI
* PostgreSQL
* Redis

### Seed the Database

Generate the telemetry dataset:

```bash
python3 data/generate.py
```

Populate PostgreSQL:

```bash
python3 -m src.seed_db
```

### Run Automated Tests

```bash
pytest tests/
```

### Stop Infrastructure

```bash
docker compose down
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
