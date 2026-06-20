# ADR-08: Hot Path Telemetry Ingestion Strategy

## Status

Accepted

---

# 1. Context

The LineGuard platform receives manufacturing telemetry originating from a synthetic conveyor-belt simulation.

Each physical observation produces multiple sensor measurements:

* Torque
* Conveyor Speed
* Fill Level

The ingestion layer must reliably persist telemetry while preventing duplicate records and maintaining predictable write performance.

The system is expected to support both:

* Real-time telemetry ingestion
* Historical dataset replay

without requiring separate storage architectures.

---

# 2. Decision

Telemetry enters the platform through a dedicated FastAPI ingestion endpoint.

```text
Telemetry Event
      ↓
POST /readings
      ↓
Pydantic Validation
      ↓
PostgreSQL Storage
```

The ingestion service is responsible only for:

* Validation
* Deduplication
* Persistence

No anomaly scoring or feature engineering occurs during ingestion.

These responsibilities are delegated to the Cold Path architecture described in ADR-07.

---

# 3. API-First Ingestion Strategy

All telemetry enters the platform through:

```http
POST /readings
```

Example payload:

```json
{
  "line_id": "Line_1",
  "sensor_type": "torque",
  "value": 152.3,
  "timestamp": "2025-09-14T10:00:00Z"
}
```

Incoming requests are validated using Pydantic schemas before database interaction occurs.

Benefits include:

* Type validation
* Timestamp validation
* Consistent request contracts
* Clear API boundaries

---

# 4. Idempotent Event Processing

Replay systems, network retries, and distributed ingestion workflows may occasionally resend identical telemetry observations.

Without protection, duplicate events would inflate telemetry volume and distort downstream feature calculations.

To prevent duplication, telemetry records are uniquely identified by:

```text
(line_id, sensor_type, timestamp)
```

A database-level uniqueness constraint enforces idempotency.

Example:

```text
Line_1
torque
2025-09-14 10:00:00
```

may only exist once.

Repeated submissions are safely ignored.

This guarantees that replay operations remain deterministic and prevents duplicate sensor observations from corrupting anomaly calculations.

---

# 5. Dataset Replay Strategy

The synthetic dataset contains:

```text
129,600 wide telemetry rows
```

which expand into:

```text
388,800 sensor events
```

during normalization.

To simulate continuous telemetry flow, a replay engine streams events through the same public ingestion API used by production clients.

Architecture:

```text
CSV Dataset
      ↓
Replay Engine
      ↓
POST /readings
      ↓
FastAPI
      ↓
PostgreSQL
```

This ensures replay testing exercises the complete ingestion stack rather than bypassing validation or persistence layers.

---

# 6. Asynchronous Batch Ingestion

The replay engine uses:

```python
asyncio
httpx.AsyncClient
```

to submit telemetry concurrently.

The stream is rate-limited to approximately:

```text
100 telemetry rows/sec
```

or:

```text
300 sensor events/sec
```

because each telemetry row generates:

* Torque
* Conveyor Speed
* Fill Level

events.

This approach provides realistic ingestion pressure while avoiding excessive resource consumption during local development.

---

# 7. Database Indexing Strategy

The primary ingestion query pattern is:

```sql
WHERE line_id = ?
AND sensor_type = ?
ORDER BY timestamp DESC
```

To support efficient retrieval, the telemetry table maintains:

```sql
CREATE INDEX idx_sensor_lookup
ON sensor_readings (
    line_id,
    sensor_type,
    timestamp DESC
);
```

---

## Why This Index?

The index aligns directly with the dominant query pattern.

Example:

```sql
SELECT *
FROM sensor_readings
WHERE line_id = 'Line_1'
AND sensor_type = 'torque'
ORDER BY timestamp DESC
LIMIT 100;
```

Without the index:

```text
Table Scan
      ↓
Sort
      ↓
Return Results
```

With the index:

```text
Index Seek
      ↓
Direct Retrieval
```

This significantly reduces query cost as telemetry volume grows.

---

# 8. Alternatives Considered

## Direct Database Loading

Architecture:

```text
CSV
 ↓
PostgreSQL
```

Rejected.

This bypasses validation, API contracts, duplicate protection, and realistic ingestion behavior.

---

## Message Queue Ingestion

Architecture:

```text
Producer
 ↓
Kafka
 ↓
Consumer
 ↓
Storage
```

Rejected.

Current telemetry volume does not justify additional operational complexity.

---

## Wide-Format Storage

Architecture:

```text
timestamp
torque
speed
fill_level
```

Rejected.

ADR-05 selected narrow EAV storage to support runtime sensor expansion and flexible telemetry schemas.

```

---

# 9. Consequences

## Positive

- Consistent ingestion interface
- Deterministic replay behavior
- Database-level duplicate protection
- Efficient telemetry retrieval
- Realistic end-to-end testing

## Negative

- Additional HTTP overhead during replay
- Increased row counts due to EAV normalization
- More complex indexing strategy than wide-table storage

---

# 10. Outcome

The platform adopts an API-first ingestion architecture.

Telemetry is validated, deduplicated, and persisted through a single operational path regardless of whether events originate from a live source or a replayed dataset.

This ensures that ingestion behavior remains consistent, observable, and extensible while providing a stable foundation for downstream anomaly detection workflows.
```
