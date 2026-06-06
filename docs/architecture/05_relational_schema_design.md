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