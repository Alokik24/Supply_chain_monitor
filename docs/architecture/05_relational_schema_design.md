# ARCH-05: Relational Schema Integrity & Hardware Mapping
Status: APPROVED

## 1. The Hardware-to-Software Decoupling

Our physical data generation simulates a real-world edge device emitting a unified, concurrent data frame (`timestamp`, `line_id`, `torque`, `conveyor_speed`, `fill_level`). This is modeled as a **Wide Row Structure**.

Our database storage engine implements a normalized **Narrow (Entity-Attribute-Value) Layout**. 

### The Ingestion Transformation Rule
The application backend (`src/seed_db.py` during initialization, and FastAPI `POST /readings` during streaming execution) acts as the normalization buffer. It intercepts the incoming wide hardware payload, iterates over the dynamic parameter dict, and generates individual, distinct rows for the database.

| Source Hardware Attribute | Database `sensor_type` Map | Database Target Table |
| :--- | :--- | :--- |
| `torque` | `'torque'` | `sensor_readings` |
| `conveyor_speed` | `'conveyor_speed'` | `sensor_readings` |
| `fill_level` | `'fill_level'` | `sensor_readings` |

## 1.1 Ingestion Transformation Rationale & Pipeline Mechanics

### Context & Design Trade-offs
We evaluated two methods for converting incoming wide hardware payloads into our normalized narrow schema:
1. **Database-Layer Normalization:** Passing a wide JSON payload to a PostgreSQL stored procedure or trigger to split the rows natively.
2. **Application-Layer Normalization:** Utilizing our Python backend processing layer (SQLAlchemy/Pandas) to unroll arrays before hitting the wire.

### Decision
We selected **Application-Layer Normalization**. 

### Empirical System Design Justification
* **Horizontal Scalability:** Unrolling matrices is CPU-bound work. Shifting this computation out of the database engine to our application layer (FastAPI nodes) ensures our stateful database storage layer only uses its processing cycles for pure ACID transactions, querying, and disk I/O.
* **Network Throughput:** By utilizing Python to format array variables into an explicit list of dictionaries, SQLAlchemy can execute a highly optimized batch insert block (`connection.execute(query, batch_records)`). This compiles the 3,000 narrow mutations into a single network packet, matching the payload efficiency of a wide write while gaining the indexing benefits of a narrow table layout.

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