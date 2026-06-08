# src/seed_db.py
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

def get_database_connection():
    """Builds a connection pool to PostgreSQL using our configuration URL."""
    # Read the individual environment variables injected by Docker Compose
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_name = os.getenv("POSTGRES_DB", "anomaly_monitor")
    
    # Inside Docker network, the host name is "database"
    host = os.getenv("POSTGRES_HOST", "database")
    port = os.getenv("POSTGRES_PORT", "5432")
    
    # Construct the final dynamic URL string
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    print(f"Connecting to infrastructure pool at: postgresql://{user}:****@{host}:{port}/{db_name}")

    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        return engine
    except Exception as e:
        print(f"CRITICAL: Failed to connect to PostgreSQL pool: {e}")
        sys.exit(1)

def apply_migrations(engine):
    """Reads our versioned schema file and builds the tables inside PostgreSQL."""
    migration_path = "db/migrations/001_init_schema.sql"
    if not os.path.exists(migration_path):
        print(f"ERROR: Migration file missing at {migration_path}")
        sys.exit(1)
        
    print("Reading and applying migration: 001_init_schema.sql...")
    with open(migration_path, "r") as f:
        schema_sql = f.read()
        
    # engine.begin() opens a database transaction block.
    # If any query fails inside this block, everything rolls back to protect our DB.
    with engine.begin() as connection:
        connection.execute(text(schema_sql))
    print("Schema tables successfully verified/created.")

def seed_telemetry_data(engine):
    """Unrolls wide hardware lines into narrow database records."""
    csv_path = "data/sensor_data.csv"
    if not os.path.exists(csv_path):
        print(f"ERROR: Missing source dataset at {csv_path}. Run generate.py first")
        sys.exit(1)
        
    # Read the first 1000 rows
    df = pd.read_csv(csv_path).head(1000)
    
    # Pre-compiling our insert command
    insert_query = text("""
        INSERT INTO sensor_readings (line_id, sensor_type, value, timestamp)
        VALUES (:line_id, :sensor_type, :value, :timestamp)
    """)
    
    batch_records = []
    
    print("Processing hardware log matrix (unrolling wide-to-narrow conversion)...")
    for _, row in df.iterrows():
        timestamp = row['timestamp']
        line_id = row['line_id']
        
        # normalization translator loop!
        # We split 1 wide row from the hardware file into 3 independent narrow entries.
        batch_records.append({"line_id": line_id, "sensor_type": "torque", "value": float(row['torque']), "timestamp": timestamp})
        batch_records.append({"line_id": line_id, "sensor_type": "conveyor_speed", "value": float(row['conveyor_speed']), "timestamp": timestamp})
        batch_records.append({"line_id": line_id, "sensor_type": "fill_level", "value": float(row['fill_level']), "timestamp": timestamp})
        
    print(f"Staging database transaction: committing {len(batch_records)} narrow entries...")
    
    with engine.begin() as connection:
        # connection.execute(..., list) tells SQLAlchemy to bundle all 3,000 entries 
        # into a single network packet for peak transactional database throughput.
        connection.execute(insert_query, batch_records)
        
    print(f"Success! Relational database populated with {len(df)} wide events ({len(batch_records)} rows).")

def run_verification_metrics(engine):
    """Queries our newly seeded tables to verify data density and types."""
    query = text("""
        SELECT sensor_type, COUNT(*), ROUND(AVG(value)::numeric, 2) as average_value
        FROM sensor_readings
        GROUP BY sensor_type;
    """)
    
    print("\n" + "="*50 + "\nDATABASE SEED VERIFICATION METRICS:\n" + "="*50)
    with engine.connect() as connection:
        results = connection.execute(query).fetchall()
        for row in results:
            print(f" Sensor Type: {row[0]:<15} | Rows Inserted: {row[1]:<5} | Calculated Mean: {row[2]}")

if __name__ == "__main__":
    db_engine = get_database_connection()
    apply_migrations(db_engine)
    seed_telemetry_data(db_engine)
    run_verification_metrics(db_engine)