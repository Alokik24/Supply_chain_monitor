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