# ARCH-01: Storage & Ingestion Baseline Selection

Status: APPROVED

Context: Supply Chain Anomaly Monitor Pipeline Setup

## 1. Relational Engine Selection: PostgreSQL vs. Alternatives

### 1.1 Context & Core Trade-offs

A common architectural pattern for dynamic, high-frequency sensor telemetry streams is to deploy a schemaless Document Store (NoSQL) like MongoDB for rapid development, or a specialized Time-Series Database (TSDB) such as TimescaleDB or InfluxDB for optimized telemetry scaling.

For this operational anomaly monitor pipeline, **PostgreSQL using a normalized Narrow / Entity-Attribute-Value (EAV) layout provides the most sustainable engineering trade-off** given current system requirements and the need to manage both telemetry and operational workflow state within a single platform.

---

### 1.2 Evaluation of Alternatives

#### PostgreSQL vs. MongoDB (NoSQL Document Approach)

* **Relational Workflow Modeling:** The system manages more than raw telemetry. Sensor readings generate anomaly cases, which in turn accumulate investigation evidence and progress through operational states (`FLAGGED` → `INVESTIGATING` → `RESOLVED`). PostgreSQL naturally models these relationships using foreign keys, constraints, and transactional consistency across multiple entities.
* **Data Integrity & Operational Simplicity:** The anomaly lifecycle relies on strongly related records spanning telemetry, case management, and evidence tracking. PostgreSQL allows these relationships to be enforced directly at the database layer, reducing application complexity and ensuring consistent state transitions throughout the investigation workflow.

#### PostgreSQL vs. Specialized Time-Series Databases (e.g., TimescaleDB, InfluxDB)

* **The Scale Frontier:** Dedicated time-series platforms are optimized for extremely high ingestion rates, automated retention policies, compression strategies, and long-term telemetry storage. For large-scale industrial deployments, these systems often represent the preferred architecture.
* **The Lifecycle Justification:** In this pipeline, telemetry data is only one component of the overall system. Sensor events generate relational entities such as anomaly cases, evidence records, and investigation workflows. Standard PostgreSQL allows the entire operational lifecycle to remain within a single transactional engine, avoiding additional synchronization layers or cross-database complexity.
* **Future Evolution Path:** If telemetry volume eventually becomes the dominant bottleneck, TimescaleDB provides a natural migration path by extending PostgreSQL with time-series optimizations while preserving the existing relational model and application architecture.

---

### 1.3 The Narrow Schema (EAV) Nuance

To achieve runtime extensibility without repeated structural migrations, the ingestion layer transforms wide-format hardware packets (`timestamp`, `line_id`, `torque`, `conveyor_speed`, `fill_level`) into individual narrow telemetry records.

This design introduces a deliberate engineering trade-off:

* **The Redundancy:** Metadata fields such as `timestamp` and `line_id` are duplicated across multiple records for a single physical observation, increasing total row count and storage consumption.
* **The Operational Alignment:** This redundancy is intentionally accepted because it enables **zero-downtime sensor expansion**. New sensor types can be introduced immediately as runtime values rather than requiring blocking `ALTER TABLE` operations on production ingestion tables.
* **The Flexibility Benefit:** The anomaly detection pipeline can process new telemetry dimensions without schema modifications, allowing the storage model to evolve alongside the factory floor rather than forcing database migrations for every hardware change.

---

## 2. In-Memory Layer Selection: Redis vs. Memcached

### 2.1 Technical Trade-Off Evaluation

While both Memcached and Redis provide extremely fast in-memory key-value access, Redis is selected because the anomaly detection pipeline requires continuous maintenance of rolling feature windows rather than simple object caching.

* **Native Ordered Data Structures:** Sliding-window analytics require efficient insertion, expiration, and retrieval of time-ordered observations. Redis provides native structures such as **Sorted Sets (`ZSET`)**, allowing feature windows to be updated atomically using operations such as `ZADD` and `ZREMRANGEBYSCORE`.
* **Reduced Application Complexity:** Without native ordered collections, the application would need to manually retrieve, deserialize, update, and rewrite entire feature windows, increasing network traffic and introducing concurrency challenges. Redis performs these operations directly within the data store.
* **Alignment with Streaming Analytics:** Real-time anomaly detection depends on continuously maintained rolling metrics such as moving averages, rolling standard deviations, and recent event histories. Redis provides a natural foundation for these streaming feature calculations without introducing additional processing layers.

### 2.2 Durability Considerations

* **Memcached Volatility:** Memcached operates entirely in memory and loses all state when a node restarts.
* **Redis Persistence:** Redis supports configurable durability through mechanisms such as Append-Only Files (AOF), enabling recovery of recently maintained feature windows after infrastructure restarts.
* **Operational Benefit:** Persistence reduces cache warm-up periods and allows anomaly scoring services to resume with historical context rather than rebuilding rolling feature windows entirely from incoming telemetry.
