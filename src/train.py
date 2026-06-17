import os
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
import joblib
from src.features import build_feature_matrix, SENSOR_TYPES


def chronological_split(df: pd.DataFrame, train_ratio: float = 0.8):
    """Splits wide data chronologically to guarantee zero future data leakage."""
    df_sorted = df.sort_values(by="timestamp").reset_index(drop=True)
    split_idx = int(len(df_sorted) * train_ratio)

    df_train = df_sorted.iloc[:split_idx].copy()
    df_test = df_sorted.iloc[split_idx:].copy()
    return df_train, df_test


def train_and_evaluate(
    csv_path: str, output_model_dir: str = "models", metrics_path: str = "metrics.json"
):
    """
    Executes a strict split-before-build pipeline to prevent any global baseline leakage.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Target data file not found at: {csv_path}")

    # 1. Load the raw wide data file directly
    df_raw = pd.read_csv(csv_path)
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])

    # 2. Split CHRONOLOGICALLY first before computing any rolling features
    df_train_raw, df_test_raw = chronological_split(df_raw, train_ratio=0.8)

    # 3. Helper to isolate telemetry, melt it, and run your features pipeline
    def process_split(df_split):
        labels = df_split["is_anomaly"].reset_index(drop=True)

        telemetry = df_split[["timestamp", "line_id"] + SENSOR_TYPES].copy()
        df_narrow = telemetry.melt(
            id_vars=["timestamp", "line_id"],
            value_vars=SENSOR_TYPES,
            var_name="sensor_type",
            value_name="value",
        )
        # Features are computed completely isolated inside this split context!
        features = build_feature_matrix(df_narrow).reset_index(drop=True)
        features["is_anomaly"] = labels
        return features

    print("Engineering features independently for train split...")
    df_train = process_split(df_train_raw)

    print("Engineering features independently for test split...")
    df_test = process_split(df_test_raw)

    # 4. Construct feature column array list
    feature_cols = []
    for sensor in SENSOR_TYPES:
        feature_cols.extend(
            [
                # f"{sensor}_rolling_mean",
                f"{sensor}_rolling_std",
                f"{sensor}_z_score",
                f"{sensor}_rate_of_change",
                # f"{sensor}_delta_from_baseline"
            ]
        )

    X_train = df_train[feature_cols]
    X_test = df_test[feature_cols]
    y_train = df_train["is_anomaly"]
    y_test = df_test["is_anomaly"]

    # 5. Train Models
    iforest = IsolationForest(contamination=0.05, random_state=42)
    iforest.fit(X_train)
    iforest_preds = np.where(iforest.predict(X_test) == -1, 1, 0)

    rf = RandomForestClassifier(
        n_estimators=100, class_weight="balanced", random_state=42
    )
    rf.fit(X_train, y_train)
    importance_df = pd.DataFrame(
        {"feature": X_train.columns, "importance": rf.feature_importances_}
    ).sort_values("importance", ascending=False)

    print(importance_df)
    rf_preds = rf.predict(X_test)

    # 6. Calculate Metrics
    p_if, r_if, f_if, _ = precision_recall_fscore_support(
        y_test, iforest_preds, average="binary", zero_division=0
    )
    p_rf, r_rf, f_rf, _ = precision_recall_fscore_support(
        y_test, rf_preds, average="binary", zero_division=0
    )

    tn_if, fp_if, fn_if, tp_if = confusion_matrix(y_test, iforest_preds).ravel()
    tn_rf, fp_rf, fn_rf, tp_rf = confusion_matrix(y_test, rf_preds).ravel()

    metrics = {
        "isolation_forest": {
            "precision": round(p_if, 4),
            "recall": round(r_if, 4),
            "f1_score": round(f_if, 4),
            "confusion_matrix": {
                "tn": int(tn_if),
                "fp": int(fp_if),
                "fn": int(fn_if),
                "tp": int(tp_if),
            },
        },
        "random_forest": {
            "precision": round(p_rf, 4),
            "recall": round(r_rf, 4),
            "f1_score": round(f_rf, 4),
            "confusion_matrix": {
                "tn": int(tn_rf),
                "fp": int(fp_rf),
                "fn": int(fn_rf),
                "tp": int(tp_rf),
            },
        },
    }

    os.makedirs(output_model_dir, exist_ok=True)
    champion_model = rf if f_rf >= f_if else iforest
    champion_name = "random_forest" if f_rf >= f_if else "isolation_forest"

    joblib.dump(champion_model, os.path.join(output_model_dir, "anomaly_detector.pkl"))
    metrics["champion_model_deployed"] = champion_name

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    # FIXED: Extraneous f-string prefix removed to clear Ruff audit compliance
    print("--- Phase 1.3 Split Validation Active ---")
    print(f"Metrics successfully written to: {metrics_path}")


if __name__ == "__main__":
    train_and_evaluate("data/sensor_data.csv")
