# ADR 07: Decoupling EAV Storage Architecture from Matrix Analytical Workloads

## Status
Accepted

## Context
Our core database layer utilizes an Entity-Attribute-Value (EAV) long-format schema to store inbound sensor telemetry. This allows high-frequency writes (`torque`, `conveyor_speed`, `fill_level`) to stream into a single append-only data table without database schema locking or structural dependency overhead.

However, mathematical computation engines (NumPy, Pandas) and machine learning profiling models (Isolation Forest) operate on multi-dimensional linear algebra planes. If statistical windowing or vectorization functions are executed directly down a vertical EAV column, the operations will cross-contaminate disparate physical units (e.g., averaging torque Newtons with fluid Liters), rendering the calculated features statistically useless.

## Decision
We decided to explicitly decouple our streaming database ingestion storage layer from our analytical data processing layer using an in-memory Extract-Transform-Load (ETL) Pivot transformation inside the application layer.

The long-format database entries will be extracted into Python memory and immediately reconstituted into a horizontal, wide-format matrix using a chronological pivot operation aligned by timestamp and asset identifiers.

## Consequences

### Positive:
* **Write Optimization Immutability:** The production database remains zero-downtime and highly optimized for rapid, asynchronous concurrent edge-device ingestion.
* **Mathematical Isolation:** Each physical sensor stream is cleanly isolated into its own independent vector array column, allowing safe execution of descriptive statistics, moving averages, and rolling Z-score calculations.
* **Model Training Alignment:** The dataset drops from 3,000 vertical rows to 1,000 unified snapshot vectors. Each row now represents a complete, synchronized state of the machine at a specific second, matching the exact inputs required by multidimensional anomaly detection models.

### Negative / Trade-offs:
* **Memory Footprint Overhead:** Reconstituting a wide matrix requires loading data chunks into local runtime RAM to execute the pivot, necessitating intentional query boundaries (like time-range slicing) when scaling to massive production scales.