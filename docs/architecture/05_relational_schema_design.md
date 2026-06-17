# ADR-05: Telemetry Representation Strategy & Relational Schema Design

## Status

Accepted

---

# 1. Context

The anomaly monitoring pipeline operates across three fundamentally different representations of the same telemetry data.

## A. Hardware Representation (Wide Format)

Physical edge devices emit a unified telemetry packet containing multiple sensor measurements captured at the same instant.

Example:

```text
timestamp, line_id, torque, conveyor_speed, fill_level
```

This representation minimizes network overhead and reflects how industrial controllers naturally transmit data.

---

## B. Storage Representation (Narrow EAV Format)

The PostgreSQL storage layer persists each measurement as an independent database row.

Example:

```text
timestamp | line_id | sensor_type      | value
------------------------------------------------
10:00     | Line_1  | torque           | 151.2
10:00     | Line_1  | conveyor_speed   | 1188.4
10:00     | Line_1  | fill_level       | 79.6
```

This Entity-Attribute-Value (EAV) layout was selected in ADR-01 because it provides:

* Efficient append-only ingestion
* Zero-downtime sensor expansion
* Consistent indexing strategy
* Reduced schema migration requirements
* Runtime flexibility for future sensor additions

---

## C. Analytical Representation (Wide Matrix Format)

Statistical analysis and machine learning models require synchronized machine-state observations.

Example:

```text
timestamp | torque | conveyor_speed | fill_level
------------------------------------------------
10:00     | 151.2  | 1188.4         | 79.6
```

Operations such as:

* Rolling statistics
* Z-score calculations
* Correlation analysis
* Feature engineering
* Machine learning inference

operate most naturally on this wide representation.

---

# 2. Decision

The system intentionally maintains separate representations for:

1. Hardware transmission
2. Database storage
3. Analytical processing

The application layer acts as the translation boundary between these representations.

## End-to-End Flow

```text
Wide Hardware Payload
        ↓
Application-Layer Normalization
        ↓
Narrow EAV Storage (PostgreSQL)
        ↓
Application-Layer Pivot
        ↓
Wide Analytical Matrix
        ↓
Feature Engineering
        ↓
Model Training / Inference
```

This architecture allows each layer to remain optimized for its primary responsibility rather than forcing a single representation across the entire pipeline.

---

# 3. Hardware-to-Storage Transformation

## Application-Layer Normalization

Incoming telemetry payloads are normalized by the application layer:

* `src/seed_db.py` during initialization
* `POST /readings` during live ingestion

The backend converts a single wide hardware payload into multiple narrow database records before insertion.

| Hardware Attribute | Database `sensor_type` |
| ------------------ | ---------------------- |
| `torque`           | `torque`               |
| `conveyor_speed`   | `conveyor_speed`       |
| `fill_level`       | `fill_level`           |

### Example Transformation

Incoming payload:

```text
Timestamp: T1
Line: Line_1

torque: 142.50
conveyor_speed: 1200.00
fill_level: 48.90
```

Becomes:

```text
(T1, Line_1, 'torque', 142.50)
(T1, Line_1, 'conveyor_speed', 1200.00)
(T1, Line_1, 'fill_level', 48.90)
```

---

## Why Application-Layer Normalization?

Two alternatives were evaluated.

### Option A: Database-Layer Normalization

PostgreSQL triggers or stored procedures split incoming payloads after arrival.

### Option B: Application-Layer Normalization

The backend performs the transformation before transmission to PostgreSQL.

### Decision

Application-Layer Normalization was selected.

### Rationale

#### Horizontal Scalability

Payload normalization is CPU-bound work.

Executing transformations within application services allows PostgreSQL resources to remain focused on:

* Transaction processing
* Query execution
* Index maintenance
* Disk I/O

#### Efficient Bulk Inserts

The application converts normalized records into batched insert payloads:

```python
connection.execute(insert_query, batch_records)
```

This allows thousands of telemetry records to be committed within a single transaction while preserving EAV flexibility.

---

# 4. Storage-to-Analytics Transformation

## Application-Layer Pivoting

While EAV is ideal for ingestion and storage, it is poorly suited for statistical analysis.

Analytical workloads require synchronized machine-state vectors.

Therefore, telemetry is extracted from PostgreSQL and pivoted into a wide matrix using Pandas.

### Storage Representation

```text
timestamp | sensor_type      | value
--------------------------------------
10:00     | torque           | 151.2
10:00     | conveyor_speed   | 1188.4
10:00     | fill_level       | 79.6
```

### Analytical Representation

```text
timestamp | torque | conveyor_speed | fill_level
------------------------------------------------
10:00     | 151.2  | 1188.4         | 79.6
```

### Why Pivot?

Many analytical operations become difficult or mathematically invalid when executed directly against EAV telemetry.

Examples include:

* Rolling Means
* Rolling Standard Deviations
* Z-Scores
* Rate-of-Change Calculations
* Correlation Analysis
* Feature Scaling
* Multivariate Anomaly Detection

Without reconstructing synchronized machine states, calculations risk mixing unrelated physical measurements and losing temporal relationships between sensors.

---

# 5. Relational Schema Design

The database layer is intentionally divided into three entities with distinct responsibilities.

## sensor_readings

Stores raw telemetry.

Characteristics:

* Append-only
* Immutable
* High-frequency writes
* Time-series event ledger

Optimized for ingestion throughput.

---

## anomaly_cases

Stores anomaly workflow state.

Characteristics:

* Mutable lifecycle records
* Investigation tracking
* Human and AI interactions

Example lifecycle:

```text
FLAGGED
    ↓
INVESTIGATING
    ↓
RESOLVED
```

Optimized for operational workflows.

---

## evidence

Stores structured anomaly explanations.

Characteristics:

* Append-only
* Linked to anomaly cases
* Supports multiple evidence records

Example:

```text
Case #101
├── Torque Spike
├── Speed Drop
└── Underfill Event
```

Optimized for auditability and extensibility.

---

# 6. Why Separate `sensor_readings` from `anomaly_cases`?

These tables serve fundamentally different workloads.

### sensor_readings

Hot Path

* High-volume inserts
* Immutable records
* Time-series storage

### anomaly_cases

Workflow Path

* Frequent updates
* State transitions
* Investigation management

Separating these concerns prevents workflow updates from interfering with telemetry ingestion and allows each table to be optimized independently.

---

# 7. Why an Append-Only `evidence` Table?

Industrial failures rarely have a single root indicator.

A conveyor jam may simultaneously generate:

* Torque spikes
* Speed degradation
* Underfill conditions

A dedicated evidence table allows multiple supporting observations to be attached to a single anomaly case.

Benefits include:

* Auditability
* Historical traceability
* Extensibility
* Multiple evidence records per case
* Future compatibility with advanced explainability systems

---

# 8. Consequences

## Positive

### Independent Optimization

Each layer is optimized for its primary responsibility.

| Layer      | Optimized For          |
| ---------- | ---------------------- |
| Hardware   | Efficient transmission |
| PostgreSQL | Ingestion & storage    |
| Analytics  | Statistics & ML        |

### Zero-Downtime Sensor Expansion

New sensor types can be added as runtime values without schema modifications.

### Cleaner Feature Engineering

Pivoted analytical matrices enable straightforward vectorized feature calculations.

### Machine Learning Compatibility

Wide matrices naturally align with:

* Isolation Forest
* Random Forest
* Future real-time scoring pipelines

---

## Negative

### Additional Transformations

Telemetry undergoes two explicit format conversions:

```text
Wide
↓
Narrow
↓
Wide
```

adding computational overhead.

### Increased Memory Usage

Pivoting requires loading telemetry into application memory.

Large analytical workloads require careful query boundaries and windowing strategies.

### Conceptual Complexity

Developers must understand multiple representations of the same telemetry depending on system context.

---

# 9. Outcome

The system intentionally separates:

## Operational Representation

Optimized for:

* Telemetry ingestion
* Storage
* Indexing
* Schema flexibility

## Analytical Representation

Optimized for:

* Statistical analysis
* Feature engineering
* Model training
* Real-time anomaly scoring

This architecture allows storage and analytical concerns to evolve independently while preserving both ingestion efficiency and machine learning compatibility.

# 10. Implementation Validation (Phase 2.1)

Following acceptance of this architecture, the telemetry ingestion platform was implemented and validated using the complete synthetic manufacturing telemetry dataset.

## Implemented Components

The architecture described in this ADR was realized through the following operational components.

### Data Generation Layer

* Synthetic telemetry generator
* 90-day manufacturing simulation
* Multi-sensor production line model

### Ingestion Layer

* FastAPI REST ingestion service
* Pydantic request validation
* Asynchronous SQLAlchemy persistence

### Storage Layer

* PostgreSQL event ledger
* Composite uniqueness constraint
* Idempotent insert operations

### Replay Infrastructure

* Asynchronous telemetry replay engine
* Rate-limited event streaming
* Concurrent HTTP ingestion testing

---

## Operational Validation

A full end-to-end replay execution was conducted against the live ingestion platform.

### Replay Results

| Metric                        | Result     |
| ----------------------------- | ---------- |
| Wide Telemetry Rows Processed | 129,600    |
| Sensor Streams Per Row        | 3          |
| Normalized Events Generated   | 388,800    |
| API Validation                | Successful |
| Database Persistence          | Successful |
| Duplicate Protection          | Verified   |
| Integration Tests             | Passed     |

The replay engine exercised the complete ingestion path:

```text
Synthetic Dataset
        ↓
Replay Engine
        ↓
FastAPI API
        ↓
Validation Layer
        ↓
PostgreSQL Storage
```

without requiring schema modifications or architectural changes.

---

## Observations

Several implementation outcomes validated the original design assumptions.

### EAV Storage Flexibility

The normalized telemetry schema successfully stored multiple sensor streams using a single relational structure.

No schema changes were required throughout development or replay execution.

### Idempotent Persistence

Database-enforced duplicate protection proved more reliable than maintaining duplicate tracking logic within the application layer.

The composite uniqueness constraint successfully absorbed replayed events and duplicate submissions.

### Separation of Concerns

Maintaining independent representations for:

* Hardware transmission
* Database storage
* Analytical processing

simplified implementation and reduced coupling between ingestion and analytical workloads.

### Replay-Based Verification

The asynchronous replay engine provided a practical mechanism for validating ingestion behavior under sustained load using realistic telemetry data.

This enabled end-to-end verification without requiring physical manufacturing equipment.

---

## Lessons Learned

### Docker Networking

Containerized services communicate through Docker network hostnames rather than localhost.

This became a critical consideration during database initialization and service orchestration.

### Database Initialization

Application startup and database schema creation should remain separate responsibilities.

Explicit schema initialization proved easier to reason about than embedding migration logic directly into service startup.

### Transaction Boundaries

Integration testing revealed several asynchronous transaction and event-loop edge cases that were resolved through isolated testing databases and dedicated session management.

### Storage Strategy

The chosen EAV design introduced additional transformation steps but substantially simplified ingestion, schema evolution, and future sensor expansion.

---

## Final Assessment

Phase 2.1 implementation validated the core decision documented in this ADR.

The architecture successfully supported:

* High-volume telemetry ingestion
* Normalized relational storage
* Idempotent event processing
* Asynchronous replay testing
* Future analytical expansion

without requiring changes to the original telemetry representation strategy.

The decision to separate hardware transmission, database storage, and analytical representations proved operationally sound and remains the recommended architecture for subsequent phases of the project.
