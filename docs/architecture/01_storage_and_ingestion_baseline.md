# ARCH-01: Storage & Ingestion Baseline Selection
Status: APPROVED

Context: Supply Chain Anomaly Monitor Pipeline Setup

## 1. Relational Engine Selection: PostgreSQL vs. MongoDB / NoSQL

### The Core Claim
"Sensor telemetry data is dynamic and rapidly scaling, therefore it should be stored in a schemaless Document Store (NoSQL) like MongoDB."

### The Empirical Verification & Refutation
This claim is false for high-integrity industrial tracking systems. We have selected PostgreSQL for two structurally verifiable reasons:

1. **Transactional Integrity and State Consistency:**
   An anomaly detection pipeline manages a state machine. 
   A raw reading transforms into a flagged case, which transitions through statuses (`FLAGGED` -> `INVESTIGATING` -> `RESOLVED`) based on automated or human investigations. PostgreSQL guarantees strict ACID compliance across these transitions using multi-row transactions and Foreign Key constraints. 
   
   MongoDB, while supporting multi-document ACID transactions since version 4.0, introduces significant latency overhead due to its distributed lock allocation model under heavy write loads.

2. **Storage and Memory Overhead of Schemaless Architectures:**
   MongoDB documents store field keys (*e.g.*, `{"sensor_type": "torque", "value": 150.0}`) inside every single record on disk. High-frequency sensor streams ingesting millions of rows will waste gigabytes of storage purely on duplicate string keys. 
   
   PostgreSQL stores the structural schema definition *once* in the table catalog; rows contain only compressed data payloads matching that static byte layout, reducing disk footprint and keeping more active indexes loaded in memory.

---

## 2. In-Memory Layer Selection: Redis vs. Memcached

### The Core Claim
"For simple key-value feature caching, Memcached and Redis perform identically."

### The Empirical Verification & Technical Trade-Off
While both systems offer sub-millisecond in-memory lookups, Redis is selected due to its data structures, which are vital for real-time time-series operations:

1. **Atomic Complex Operations:**
   To calculate rolling window features on the hot path without a slow database query, we must maintain a moving window of sensor records. Memcached only supports primitive strings; updating a window would require downloading the entire array, modifying it in application memory, and sending it back, creating a race condition under high concurrency. 
   
   Redis supports native atomic data structures like **Sorted Sets (`ZSET`)**. We can execute an atomic write (`ZADD`) and simultaneously trim expired historical records (`ZREMRANGEBYSCORE`) in a single network trip, ensuring thread-safe, real-time window tracking.

2. **Persistence and Crash Recovery:**
   Memcached is purely volatile. If the container restarts, all feature cache histories vanish, blinding our anomaly scoring layer until enough new data points arrive. 
   
   Redis supports Append-Only File (AOF) logging, allowing fast state recovery during infrastructure restarts without dropping operational visibility.