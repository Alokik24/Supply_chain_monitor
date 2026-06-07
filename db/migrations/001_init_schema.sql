-- db/migrations/001_init_schema.sql

-- 1. Raw Telemetry Event Ledger (High-frequency append-only hot path)
CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    line_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL, -- Evaluates to: 'torque', 'conveyor_speed', 'fill_level'
    value DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL --
);

-- Indexing composite layout to keep our sliding time-window features blazing fast
CREATE INDEX IF NOT EXISTS idx_sensor_telemetry_lookup 
ON sensor_readings (line_id, sensor_type, timestamp DESC);

-- 2. Anomaly Incident Tickets (Mutable workflow state machine)
CREATE TABLE IF NOT EXISTS anomaly_cases (
    id BIGSERIAL PRIMARY KEY,
    reading_id BIGINT UNIQUE NOT NULL, -- Strict one-to-one link to the trigger reading
    status VARCHAR(30) NOT NULL DEFAULT 'FLAGGED', -- States: FLAGGED, INVESTIGATING, RESOLVED
    score DOUBLE PRECISION NOT NULL, -- Machine Learning inference anomaly score
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, --
    FOREIGN KEY (reading_id) REFERENCES sensor_readings(id) ON DELETE CASCADE
);

-- 3. Case Evidence Records (Append-only investigation forensic proof logs)
CREATE TABLE IF NOT EXISTS evidence (
    id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL, -- Foreign key pointing back to parent incident ticket
    type VARCHAR(50) NOT NULL, -- Categories: e.g., 'torque_spike', 'speed_crash', 'underfill'
    value VARCHAR(255) NOT NULL, -- String snapshot data explaining the anomaly deviation
    confidence DOUBLE PRECISION NOT NULL, --
    FOREIGN KEY (case_id) REFERENCES anomaly_cases(id) ON DELETE CASCADE
);