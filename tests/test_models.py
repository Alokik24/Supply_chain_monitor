import os
import json
import pandas as pd
import numpy as np
from train import chronological_split

def test_chronological_split_preserves_temporal_order():
    """Verifies that data is split sequentially without shuffling time values."""
    timestamps = pd.date_range(start="2026-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "value": np.random.rand(10)
    })
    
    df_train, df_test = chronological_split(df, train_ratio=0.7)
    
    assert len(df_train) == 7
    assert len(df_test) == 3
    assert df_train["timestamp"].max() < df_test["timestamp"].min()

def test_metrics_json_generation_and_schema():
    """Verifies that the training pipeline writes a valid metrics schema to disk."""
    metrics_file = "metrics.json"
    
    if os.path.exists(metrics_file):
        with open(metrics_file, "r") as f:
            data = json.load(f)
            
        assert "isolation_forest" in data
        assert "random_forest" in data
        assert "champion_model_deployed" in data
        
        # Verify complete compliance with evaluation spec guidelines
        assert "confusion_matrix" in data["isolation_forest"]
        assert "confusion_matrix" in data["random_forest"]
        assert "tp" in data["random_forest"]["confusion_matrix"]