# ARCH-01: Storage & Ingestion Baseline Selection
Status: APPROVED

Context: Supply Chain Anomaly Monitor Pipeline Setup

## 1. Relational Engine Selection: PostgreSQL vs. Alternatives

### 1.1 Context & Core Trade-offs
A common architectural pattern for dynamic, high-frequency sensor telemetry streams is to deploy a schemaless Document Store (NoSQL) like MongoDB for rapid development, or a specialized Time-Series Database (TSDB) like TimescaleDB or InfluxDB for optimized volumetric scaling. 

For this specific operational anomaly monitor pipeline, **PostgreSQL using a normalized Narrow / Entity-Attribute-Value (EAV) layout provides the most sustainable engineering trade-off** given our current constraints and the need for tight transactional state tracking.

---

### 1.2 Evaluation of Alternatives

#### PostgreSQL vs. MongoDB (NoSQL Document Approach)
* **Transactional State Consistency:** The anomaly detection layer functions as an operational state machine where a raw reading triggers a tracked case, transitioning through sequential workflows (`FLAGGED` -> `INVESTIGATING` -> `RESOLVED`). PostgreSQL handles these multi-table operations reliably through its native relational integrity and ACID compliance. While MongoDB supports multi-document transactions, its distributed locking mechanisms can introduce unpredictable latency overhead under continuous, high-concurrency write loops.
* **Byte Optimization and Memory Efficiency:** MongoDB documents serialize field keys directly into every single record on disk, which can introduce storage and memory bloat over extended high-frequency runs. PostgreSQL defines the structure once in the table catalog, storing only compressed data payloads matching that static byte layout in memory blocks, allowing a larger percentage of active indexes to remain resident in RAM.

#### PostgreSQL vs. Specialized Time-Series Databases (e.g., TimescaleDB, InfluxDB)
* **The Scale Frontier:** For absolute volumetric write performance and automated data retention lifecycles (such as compression algorithms designed for time-series data), dedicated engines like InfluxDB or TimescaleDB (which runs as a Postgres extension) are the industry standard for large-scale deployments.
* **The Lifecycle Justification:** In our pipeline, telemetry data does not simply sit in a passive analytical append-log. It directly generates complex, non-time-series relational entities: user investigation logs, audit trails, and multi-variable evidence records. Using standard PostgreSQL allows us to keep our core architecture simple by containing the entire operational lifecycle within a single database engine, avoiding the complexity of cross-database joins or external syncing tools.

---

### 1.3 The Narrow Schema (EAV) Nuance

To achieve runtime extensibility without running risky structural migrations, this architecture maps physical wide-format hardware packets (`timestamp`, `line_id`, `torque`, `conveyor_speed`, `fill_level`) into distinct, narrow database rows at the ingestion layer.

This design introduces a specific engineering penalty:
* **The Redundancy:** Metadata fields like `timestamp` and `line_id` are duplicated across multiple records for a single physical time step, increasing overall row volume.
* **The Operational Alignment:** We accept this row-bloat and localized storage redundancy because it provides a critical production benefit: **zero-downtime sensor expansions**. We can introduce entirely new sensor lines or types to the factory floor at runtime as text variables without executing blocking `ALTER TABLE` schema modifications on live ingestion tables.

---

## 2. In-Memory Layer Selection: Redis vs. Memcached

### 2.1 Technical Trade-Off Evaluation
While both Memcached and Redis provide exceptional sub-millisecond key-value lookups in memory, Redis is selected to handle the sliding feature metrics required by our real-time streaming path.

* **Atomic Aggregations vs. Application Overhead:** Computing rolling time-window features (such as 30-minute standard deviations) on the hot path requires a continuous, sliding in-memory queue of recent metrics. Memcached handles only primitive string blobs; updating a window would require the application layer to download the entire array, modify it, and write it back, which creates immediate race conditions under high concurrency. Redis resolves this via native, atomic data structures like **Sorted Sets (`ZSET`)**, allowing us to execute a write (`ZADD`) and simultaneously evict expired metrics (`ZREMRANGEBYSCORE`) in a single, thread-safe network trip.
* **State Durability:** Memcached is entirely volatile. If an instance restarts due to a network or container fault, the feature cache vanishes instantly, blinding the anomaly scoring engine until enough new data points arrive. Redis provides configurable durability via Append-Only File (AOF) logging, enabling fast state recovery during infrastructure lifecycles without cold-start blind spots.