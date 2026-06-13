# Developer Log: Phase 1.2 — Real-Time Feature Store Architecture

## The Core Problem Block
In this system, high-velocity supply chain sensors write raw event logs to PostgreSQL at a peak volume of 100 events per second. Our Isolation Forest machine learning model requires a rolling 30-minute statistical window (mean, standard deviation, and Z-score) to execute anomaly scoring on incoming telemetry data points. 

If the application attempts to compute these rolling metrics synchronously on the live ingestion path using heavy SQL aggregates or window functions over millions of raw historical database rows, the database CPU will saturate, leading to table deadlocks, connection timeouts, and pipeline failure.

## The Architecture Solution: Decoupling Compute from Serving
To solve this performance bottleneck, we implemented the M8 Feature Store Pattern by strictly decoupling our write path from our analytical execution loop:

### 1. The Hot Path (Fast Ingestion)
When a sensor submits data to `POST /readings`, the FastAPI backend performs zero mathematical computations. It validates the record schema via Pydantic, checks a composite natural idempotency key to block duplicate writes, appends the raw row to PostgreSQL, and instantly returns a `200 OK` response. This execution path takes less than 5 milliseconds.

### 2. The Cold Path (Asynchronous Feature Store)
Completely separate from the live ingestion pipeline, an isolated background worker process executes periodically. This worker runs an optimized database query using an index-backed SQL window function to pull only the warm history slice (the last-N records per sensor group). 

It feeds this minimal dataframe into `src/features.py` to compute vector transformations, then immediately flushes the updated metrics into a local Redis cache as a fast key-value store with a short Time-To-Live (TTL).

### 3. The Real-Time Scoring Loop
When the machine learning model runs inline inference, it bypasses PostgreSQL entirely. It reads the pre-computed 30-minute baseline metrics directly out of Redis memory in under 2 milliseconds, executes the model score, and flags anomalies safely without putting any read load on our transactional database tables.

## Technical Interview Q&A Breakdown

### Question:
"How do you serve machine learning features in real-time without constantly querying raw transactional database tables under high streaming load?"

### System Design Answer:
"You cannot query raw transactional tables on the hot path without risking query timeouts. To solve this, I implemented a decoupled Feature Store pattern. The ingestion path handles strict, append-only database writes. Concurrently, an asynchronous background pipeline periodically pulls a small history window slice from PostgreSQL, executes vector calculations via Pandas to derive the statistical baseline metrics (rolling means, standard deviations, and Z-scores), and updates an in-memory Redis cache. 

When the machine learning model requires feature vectors for inference, it pulls them directly out of Redis memory with a sub-2ms retrieval latency. This architecture isolates our core database write path from concurrent analytical read queries, allowing the ingestion platform to scale predictably."

### Strategic System Design Tradeoffs
* **Sacrifice Made:** We traded strict real-time data consistency for eventual consistency. Because the background feature calculation engine updates the cache in periodic batches, our rolling statistical averages may lag behind the live state by a few seconds. For industrial conveyor or asset tracking use cases, this brief propagation delay is completely acceptable.
* **Victory Gained:** We achieved total read-isolation on our primary database. No matter how many analytical queries or frontend dashboard nodes pull data from the platform, our core transactional write pipeline remains entirely unburdened.