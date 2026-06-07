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
* **Fill Level ($F$):** Measures container liquid volume. Baseline of $80\%$ volume with stable noise variance $\sigma = 1$.

### Correlated Failure Mode: Mechanical Conveyor Jam
Anomalies comprise **strictly 5%** of total system runtime and simulate a physical line jam where all three attributes break operational limits simultaneously:
* **Torque Reaction:** Sudden positive uniform spike ($+50\text{ Nm}$ to $+100\text{ Nm}$) as the motor strains against physical friction.
* **Speed Reaction:** Catastrophic negative uniform drop ($-300\text{ RPM}$ to $-500\text{ RPM}$) as the line grinds to a halt.
* **Fill Level Reaction:** Severe drop ($-20\%$ to $-40\%$) as bottle misalignments under the filling nozzles cause liquid spillage and underfills.

## Architectural Data Mapping

To guarantee zero-downtime extensibility when adding new physical hardware sensors later, this pipeline explicitly uncouples the hardware data collection from the relational database storage layer:

* **The Edge Layer:** The data generator simulates real-world hardware by outputting a **Wide Payload Data Frame** (`timestamp, line_id, torque, conveyor_speed, fill_level, is_anomaly`).
* **The Storage Layer:** Our application backend intercepts this wide payload and unrolls it into an asset-agnostic **Narrow Schema Layout** inside PostgreSQL (`id, line_id, sensor_type, value, timestamp`), allowing new sensor lines to be added dynamically as simple runtime string parameters.


## Deep-Dive Architecture Decisions (ARCH-05)

### 1. Why Separate `sensor_readings` from `anomaly_cases`?
* **The Hot-Path / Cold-Path Split Pattern:** `sensor_readings` operates as a high-frequency, append-only, entirely immutable event ledger. It is optimized exclusively to handle raw ingestion writes at production speed. Conversely, `anomaly_cases` functions as a highly mutable transactional state machine tracking ongoing human and AI agent lifecycle investigations (`FLAGGED` -> `INVESTIGATING` -> `RESOLVED`).
* **Lock Elimination:** Separating these spaces ensures that when an operator or AI agent updates the status of an active incident ticket, row-level database transactional locks are isolated strictly to the minor `anomaly_cases` table. The core high-speed ingestion telemetry path (`sensor_readings`) remains completely unblocked, preventing ingestion latency drift or dropped packets.

### 2. Why Implement an Append-Only `evidence` Table?
* **Forensic Audit Integrity:** In regulated supply chain and industrial environments, safety diagnostics cannot simply be overwritten or cleared. If an analytical asset links a system failure to a specific variable deviation, that diagnostic proof record must be permanently preserved.
* **Relational Extensibility:** A mechanical breakdown on a factory floor is rarely caused by an isolated variable spike. A conveyor jam simultaneously causes torque spikes, belt speed degradation, and fluid underfills. Keeping `evidence` as a dedicated child table linked via a foreign key (`case_id`) allows our evaluation layers to append infinite structural proof points over time without running destructive schema alterations on the master tables.

## Hardware Payload Normalization (Wide-to-Narrow)

Our telemetry ingestion pipeline bridges the gap between hardware execution models and optimized storage schemas. 

* **The Hardware Reality (Wide Stream):** Physical edge controllers emit data as a single, concurrent horizontal payload package to reduce device network overhead.
* **The Storage Reality (Narrow Ledger):** PostgreSQL stores records vertically as an Entity-Attribute-Value (EAV) layout to prevent null-column fragmentation and ensure hyper-efficient time-window lookups.

### The Transformation Blueprint

When a data packet is intercepted by our ingestion engines (`src/seed_db.py` or `POST /readings`), it is instantly unrolled:

```text
[ Incoming Hardware Frame ]
  │  (Timestamp: T1, Line: Line_1)
  ├──► torque: 142.50         ──► DB Row 1: (T1, Line_1, 'torque', 142.50)
  ├──► conveyor_speed: 1200.0 ──► DB Row 2: (T1, Line_1, 'conveyor_speed', 1200.0)
  └──► fill_level: 48.90      ──► DB Row 3: (T1, Line_1, 'fill_level', 48.90)
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
1. **Initialize Virtual Environment Isolation**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Run Deterministic Telemetry Generation**

```bash
python3 data/generate.py
```
3. **Verify Baseline Matrix Integrity**

```bash
python3 -c "import pandas as pd; df = pd.read_csv('data/sensor_data.csv'); print(df.groupby('is_anomaly').mean())"
```

