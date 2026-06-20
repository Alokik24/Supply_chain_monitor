# ADR-07: Cold-Path Scoring Pipeline & Watermark-Based Processing

## Status

Accepted

# 1. Context

The telemetry ingestion platform continuously receives sensor observations from the manufacturing telemetry stream.

The ingestion workload and anomaly detection workload have fundamentally different operational characteristics.

### Telemetry Ingestion

The ingestion path must:

* Accept incoming telemetry
* Validate payloads
* Persist readings
* Return responses immediately

Primary objective:

```text
Reliable event capture
```

---

### Anomaly Detection

Anomaly detection requires substantially more computation.

Each evaluation cycle must:

* Retrieve historical telemetry
* Reconstruct synchronized machine state
* Generate engineered features
* Execute machine learning inference
* Create anomaly cases
* Update operational caches

Primary objective:

```text
Accurate machine-state evaluation
```

Combining these responsibilities within a single request-response cycle would couple telemetry throughput directly to machine-learning execution latency.

---

# 2. Decision

The platform separates telemetry ingestion and anomaly scoring into independent execution paths.

## Hot Path

The ingestion API performs:

```text
Telemetry
    ↓
Validation
    ↓
PostgreSQL Storage
    ↓
Response
```

The ingestion service does not execute:

* Feature engineering
* Historical aggregation
* Statistical calculations
* Machine learning inference

This keeps ingestion latency predictable regardless of model complexity.

---

## Cold Path

A dedicated scoring worker executes asynchronously.

```text
New Readings
      ↓
Watermark Lookup
      ↓
Historical Context Retrieval
      ↓
Feature Engineering
      ↓
Model Inference
      ↓
Case Creation
      ↓
Redis Cache Update
      ↓
Watermark Advance
```

The worker operates independently of client requests and can continue processing telemetry even when no operators are connected to the dashboard.

---

# 3. Watermark-Based Processing Strategy

The scoring engine maintains processing progress using Redis.

```text
scoring_watermark:last_processed_id
```

The watermark stores the highest telemetry record successfully processed by the scoring engine.

### Execution Flow

```text
Redis Watermark
        ↓
Retrieve New Readings
(id > watermark)
        ↓
Process Batch
        ↓
Commit Results
        ↓
Advance Watermark
```

This approach guarantees that previously evaluated telemetry is not repeatedly rescored.

### Why a Watermark?

Alternative approaches such as:

* Boolean processed flags
* Full-table rescans
* Timestamp polling

would introduce additional storage overhead or increasingly expensive database queries as telemetry volume grows.

The watermark strategy allows processing complexity to remain proportional to newly arrived data.

---

# 4. Feature Engineering Boundary

The scoring worker serves as the boundary between operational storage and analytical processing.

Telemetry is stored in PostgreSQL using the narrow EAV representation defined in ADR-05.

Before inference, telemetry is reconstructed into a synchronized analytical matrix through application-layer pivoting.

```text
Narrow EAV Storage
        ↓
Wide Analytical Matrix
        ↓
Rolling Statistics
        ↓
Z-Scores
        ↓
Rate-of-Change Features
        ↓
Model Inference
```

This preserves storage flexibility while maintaining compatibility with the model evaluation framework defined in ARCH-03.

---

# 5. Anomaly Case Creation

The scoring worker does not modify telemetry records.

Instead, anomaly detections create independent workflow entities.

```text
Telemetry
      ↓
Model Score
      ↓
Anomaly Case
      ↓
FLAGGED
```

Operational workflows remain isolated from telemetry storage.

This separation allows investigation lifecycles to evolve independently from ingestion workloads.

Example:

```text
FLAGGED
    ↓
INVESTIGATING
    ↓
RESOLVED
```

---

# 6. Redis Feature Cache

Following successful inference, engineered feature summaries are cached in Redis.

Example key:

```text
features:{line_id}:{sensor_type}
```

Stored values include:

* Rolling Mean
* Rolling Standard Deviation
* Z-Score

TTL:

```text
600 seconds
```

The cache supports future investigation tooling and low-latency feature retrieval without repeatedly recomputing historical statistics.

---

# 7. Alternatives Considered

## A. Synchronous Scoring During Ingestion

Architecture:

```text
Telemetry
    ↓
Validation
    ↓
Feature Engineering
    ↓
Model Inference
    ↓
Storage
```

Rejected.

Machine-learning execution would directly increase ingestion latency and reduce throughput.

---

## B. Database Trigger-Based Scoring

Architecture:

```text
Insert
    ↓
Database Trigger
    ↓
Inference Logic
```

Rejected.

This would tightly couple analytical processing with relational storage responsibilities and complicate operational debugging.

---

## C. Full Dataset Rescoring

Architecture:

```text
Entire Dataset
      ↓
Inference
      ↓
Repeat
```

Rejected.

Computational cost grows linearly with historical telemetry volume and becomes increasingly inefficient as the dataset expands.

---

# 8. Consequences

## Positive

### Independent Scaling

Telemetry ingestion and anomaly scoring can evolve independently.

### Predictable API Performance

Ingestion latency remains largely unaffected by model complexity.

### Replay Compatibility

Historical telemetry datasets can be replayed through the scoring pipeline without modifying ingestion behavior.

### Efficient Incremental Processing

The watermark mechanism prevents redundant rescoring of previously evaluated observations.

### Future Extensibility

Additional models, explainability layers, or investigation agents can be attached to the scoring worker without impacting ingestion services.

---

## Negative

### Eventual Consistency

Anomaly cases are not created immediately after telemetry arrival.

A short delay exists between ingestion and detection.

### Additional Infrastructure

The architecture introduces:

* Worker lifecycle management
* Redis state management
* Watermark coordination

### Operational Complexity

Failures must be diagnosed across multiple independent processing components rather than a single request path.

---

# 9. Outcome

The platform intentionally adopts a Hot Path / Cold Path architecture.

The Hot Path remains optimized for telemetry ingestion and durable storage.

The Cold Path remains optimized for feature engineering, machine learning inference, anomaly creation, and future AI-driven investigation workflows.

This separation allows ingestion throughput, analytical complexity, and operational workflows to evolve independently while preserving predictable system behavior under increasing telemetry volume.
