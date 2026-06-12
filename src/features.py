import pandas as pd
import numpy as np
from sqlalchemy import Engine


SENSOR_TYPES = ["conveyor_speed", "fill_level", "torque"]
WINDOW = 30  # 30-minute rolling window

def pivot_to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts narrow entity-attribute-value (EAV) rows from the DB into a wide matrix.
    Safely enforces chronological sorting to ensure rolling calculations run forward.
    """
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "line_id"] + SENSOR_TYPES)
        
    df_wide = df.pivot(
        index=["timestamp", "line_id"],
        columns="sensor_type",
        values="value"
    ).reset_index()

    df_wide.columns.name = None  
    
    # CRITICAL FIX: Ensure data runs from oldest to newest before computing windows
    return df_wide.sort_values(by=["line_id", "timestamp"]).reset_index(drop=True)


def compute_rolling_features(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Computes rolling metrics grouped by line_id to prevent cross-factory contamination.
    """
    df = df_wide.copy()
    
    for sensor in SENSOR_TYPES:
        if sensor not in df.columns:
            df[sensor] = np.nan  # Gracefully keep standard schema columns intact

        # CRITICAL FIX: Isolate rolling metrics per physical production line
        grouped_roll = df.groupby("line_id")[sensor].transform(
            lambda x: x.rolling(window=WINDOW, min_periods=1).mean()
        )
        grouped_std = df.groupby("line_id")[sensor].transform(
            lambda x: x.rolling(window=WINDOW, min_periods=1).std()
        ).fillna(0)

        df[f"{sensor}_rolling_mean"] = grouped_roll
        df[f"{sensor}_rolling_std"] = grouped_std
        
        # Safe Z-score calculation to eliminate potential division by zero
        df[f"{sensor}_z_score"] = (df[sensor] - df[f"{sensor}_rolling_mean"]) / (df[f"{sensor}_rolling_std"] + 1e-6)

    return df


def compute_rate_of_change(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Computes delta changes grouped by line_id to capture sharp velocity variations.
    """
    df = df_wide.copy()
    for sensor in SENSOR_TYPES:
        if sensor in df.columns:
            df[f"{sensor}_rate_of_change"] = df.groupby("line_id")[sensor].diff().fillna(0)
    return df


def compute_delta_from_baseline(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Computes variance against the window baseline slice context.
    """
    df = df_wide.copy()
    for sensor in SENSOR_TYPES:
        if sensor in df.columns:
            # Grouped transform ensures we compare records to their specific line profile
            line_mean = df.groupby("line_id")[sensor].transform("mean")
            df[f"{sensor}_delta_from_baseline"] = df[sensor] - line_mean
    return df


def build_feature_matrix(df_narrow: pd.DataFrame) -> pd.DataFrame:
    """
    Master pipeline wrapper. Handles empty records cleanly to ensure zero runtime crashes.
    """
    if df_narrow.empty:
        raise ValueError("Cannot build feature matrix from empty telemetry DataFrame.")
        
    df = pivot_to_wide(df_narrow)
    df = compute_rolling_features(df)
    df = compute_rate_of_change(df)
    df = compute_delta_from_baseline(df)
    return df

def generate_window_fetch_query(window_size: int = 30) -> str:
    """
    Constructs an optimized SQL query using window functions to pull 
    the exact history size needed per sensor to compute rolling metrics.
    """
    # Safety margin: We pull a few extra rows per sensor group to 
    # guarantee we have enough data points to compute rate of change.
    history_limit = window_size + 5
    
    query = f"""
    WITH ranked_readings AS (
        SELECT 
            id, 
            line_id, 
            sensor_type, 
            value, 
            timestamp,
            ROW_NUMBER() OVER (
                PARTITION BY line_id, sensor_type 
                ORDER BY timestamp DESC
            ) as rank
        FROM sensor_readings
    )
    SELECT id, line_id, sensor_type, value, timestamp
    FROM ranked_readings
    WHERE rank <= {history_limit}
    ORDER BY line_id, sensor_type, timestamp ASC;
    """
    return query

def fetch_historical_window_dataframe(db_engine: Engine, window_size: int = 30) -> pd.DataFrame:
    """
    Executes the optimized window query against PostgreSQL and returns 
    a chronological narrow DataFrame ready for feature processing.
    """
    # 1. Generate our optimized window raw SQL string query
    sql_query_string = generate_window_fetch_query(window_size=window_size)
    
    # 2. Safely open a database connection context block and read the rows
    with db_engine.connect() as connection:
        df_narrow = pd.read_sql_query(
            sql=sql_query_string,
            con=connection,
            parse_dates=["timestamp"]  # Forces explicit time parsing to prevent index bugs
        )
        
    return df_narrow