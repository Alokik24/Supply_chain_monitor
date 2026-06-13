# tests/test_features.py
import pandas as pd
import pytest
from src.features import (
    pivot_to_wide,
    compute_rolling_features,
    compute_rate_of_change,
    compute_delta_from_baseline,
    build_feature_matrix,
    generate_window_fetch_query
)

@pytest.fixture
def narrow_df():
    """
    Minimal valid narrow EAV DataFrame mimicking raw DB output.
    2 timestamps x 3 sensors = 6 rows.
    """
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6],
        "line_id": ["Line_1"] * 6,
        "sensor_type": ["torque", "conveyor_speed", "fill_level"] * 2,
        "value": [150.0, 1200.0, 80.0, 200.0, 900.0, 60.0],
        "timestamp": pd.to_datetime([
            "2026-01-01 00:00", "2026-01-01 00:00", "2026-01-01 00:00",
            "2026-01-01 00:01", "2026-01-01 00:01", "2026-01-01 00:01",
        ])
    })

# ─── TASK 1: TESTING SYSTEM MATRICES AND SCHEMAS ───

def test_build_feature_matrix_shape_and_columns(narrow_df):
    """
    Validates that the master execution function collapses narrow inputs cleanly 
    and appends all 15 expected production telemetry schema feature columns.
    """
    feature_matrix = build_feature_matrix(narrow_df)
    
    # 6 narrow rows across 3 distinct sensors must pivot into exactly 2 wide rows
    assert len(feature_matrix) == 2
    assert feature_matrix.loc[0, "line_id"] == "Line_1"
    
    # Verify the engineering schema contains our operational metrics
    expected_metrics = [
        "conveyor_speed_rolling_mean", "conveyor_speed_rolling_std", "conveyor_speed_z_score",
        "conveyor_speed_rate_of_change", "conveyor_speed_delta_from_baseline",
        "torque_z_score", "fill_level_z_score"
    ]
    for metric in expected_metrics:
        assert metric in feature_matrix.columns

# ─── TASK 2: TESTING BOUNDARY CONDITION EDGE CASES ───

def test_feature_pipeline_empty_input_boundary():
    """
    Asserts that passing an empty database telemetry slice explicitly raises 
    a managed ValueError instead of dropping into unhandled runtime errors.
    """
    empty_narrow_df = pd.DataFrame(columns=["id", "line_id", "sensor_type", "value", "timestamp"])
    
    with pytest.raises(ValueError, match="Cannot build feature matrix from empty telemetry DataFrame"):
        build_feature_matrix(empty_narrow_df)


def test_feature_pipeline_single_row_warmup():
    """
    Tests the single-row startup state to guarantee our 1e-6 modifier 
    safely catches NaN variances and converts them into stable 0.0 metrics.
    """
    single_row_df = pd.DataFrame({
        "id": [1],
        "line_id": ["Line_1"],
        "sensor_type": ["torque"],
        "value": [150.0],
        "timestamp": pd.to_datetime(["2026-01-01 00:00"])
    })
    
    feature_matrix = build_feature_matrix(single_row_df)
    
    # Single-row std deviations evaluate to NaN in Pandas; assert our code casts it safely to 0
    assert feature_matrix.loc[0, "torque_rolling_std"] == 0.0
    # Safe fallback mapping should calculate an explicit 0.0 Z-Score vector
    assert pytest.approx(feature_matrix.loc[0, "torque_z_score"]) == 0.0

# ─── TASK 3: TESTING RE-ORDERING AND MULTI-LINE PATHS ───

def test_pivot_to_wide_enforces_chronological_sorting():
    """
    Verifies that regardless of how randomly database shards return raw records, 
    the pipeline explicitly forces chronological sorting before running windows.
    """
    scrambled_df = pd.DataFrame({
        "id": [2, 1],
        "line_id": ["Line_1", "Line_1"],
        "sensor_type": ["torque", "torque"],
        "value": [200.0, 100.0],
        "timestamp": pd.to_datetime(["2026-01-01 00:05", "2026-01-01 00:01"]) # Newest row listed first
    })
    
    wide_df = pivot_to_wide(scrambled_df)
    
    # Row index 0 must be the oldest historic timestamp record to protect downstream metrics
    assert wide_df.loc[0, "timestamp"] == pd.to_datetime("2026-01-01 00:01")
    assert wide_df.loc[0, "torque"] == 100.0


def test_cross_factory_line_isolation():
    """
    Critical validation check. Confirms that rolling metrics do not leak 
    statistics across separate, independent manufacturing lines.
    """
    multi_line_df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "line_id": ["Line_1", "Line_1", "Line_2", "Line_2"],
        "sensor_type": ["torque"] * 4,
        "value": [100.0, 110.0, 900.0, 910.0], # Line 2 operates at a vastly higher numeric scope
        "timestamp": pd.to_datetime(["2026-01-01 00:00", "2026-01-01 00:01"] * 2)
    })
    
    feature_matrix = build_feature_matrix(multi_line_df)
    
    line_1_results = feature_matrix[feature_matrix["line_id"] == "Line_1"].reset_index(drop=True)
    line_2_results = feature_matrix[feature_matrix["line_id"] == "Line_2"].reset_index(drop=True)
    
    # If isolation holds, line_1's delta from baseline evaluates strictly against its own line mean
    # Line 1 mean = 105.0. Row 0 delta = 100.0 - 105.0 = -5.0
    assert pytest.approx(line_1_results.loc[0, "torque_delta_from_baseline"]) == -5.0
    
    # Line 2 mean = 905.0. Row 0 delta = 900.0 - 905.0 = -5.0
    # If the metrics had leaked across, Line 2's high magnitude values would skew Line 1's delta to <-400
    assert pytest.approx(line_2_results.loc[0, "torque_delta_from_baseline"]) == -5.0

# ─── TASK 4: ISOLATED UNIT TESTING FOR TRANSFORMATION MODULES ───

def test_compute_rolling_features_isolated(narrow_df):
    """
    Unit Test: Explicitly targets compute_rolling_features using a pre-pivoted wide matrix.
    Validates mathematical correctness of the statistical window.
    """
    # 1. Prepare clean, wide-format input baseline
    df_wide = pivot_to_wide(narrow_df)
    
    # 2. Execute only the rolling feature computation module
    processed_df = compute_rolling_features(df_wide)
    
    # 3. Assertions: Verify specific calculations on row data points
    # Line_1 torque values are 150.0 at 00:00 and 200.0 at 00:01. Mean = 175.0
    assert pytest.approx(processed_df.loc[1, "torque_rolling_mean"]) == 175.0
    
    # Volatility validation: Std dev of [150.0, 200.0] is exactly 35.3553
    assert pytest.approx(processed_df.loc[1, "torque_rolling_std"], rel=1e-3) == 35.3553
    
    # Z-Score validation for row index 1: (200.0 - 175.0) / (35.3553 + 1e-6) ~= 0.7071
    assert pytest.approx(processed_df.loc[1, "torque_z_score"], rel=1e-3) == 0.7071


def test_compute_rate_of_change_isolated(narrow_df):
    """
    Unit Test: Explicitly targets compute_rate_of_change.
    Validates that sequential delta surges are captured accurately.
    """
    df_wide = pivot_to_wide(narrow_df)
    
    # Execute only the rate of change calculation module
    processed_df = compute_rate_of_change(df_wide)
    
    # Row index 0 has no prior record context -> diff defaults to 0.0
    assert processed_df.loc[0, "conveyor_speed_rate_of_change"] == 0.0
    
    # Row index 1 conveyor_speed moves from 1200.0 to 900.0 -> delta change = -300.0
    assert processed_df.loc[1, "conveyor_speed_rate_of_change"] == -300.0


def test_compute_delta_from_baseline_isolated(narrow_df):
    """
    Unit Test: Explicitly targets compute_delta_from_baseline.
    Validates tracking of slow variance drifts away from the global average.
    """
    df_wide = pivot_to_wide(narrow_df)
    
    # Execute only the baseline drift calculation module
    processed_df = compute_delta_from_baseline(df_wide)
    
    # Conveyor speed values: 1200.0 and 900.0. Global Mean = 1050.0
    # Row index 0 baseline drift variance = 1200.0 - 1050.0 = 150.0
    assert pytest.approx(processed_df.loc[0, "conveyor_speed_delta_from_baseline"]) == 150.0
    
    # Row index 1 baseline drift variance = 900.0 - 1050.0 = -150.0
    assert pytest.approx(processed_df.loc[1, "conveyor_speed_delta_from_baseline"]) == -150.0

def test_generate_window_fetch_query_syntax():
    """
    Unit Test: Verifies that the SQL generator constructs a valid string 
    containing our critical partitioning window keywords.
    """
    # 1. Generate the raw SQL text string
    sql_text = generate_window_fetch_query(window_size=30)
    
    # 2. Assertions: Ensure the string is not empty and contains core structural operators
    assert isinstance(sql_text, str)
    assert "PARTITION BY line_id, sensor_type" in sql_text
    assert "ROW_NUMBER()" in sql_text
    assert "ranked_readings" in sql_text
    
    # Verify our history buffer logic (window_size 30 + 5 = 35)
    assert "rank <= 35" in sql_text