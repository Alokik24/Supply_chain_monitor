# ADR-06: Retain Current Synthetic Dataset and Document Evaluation Limitations

## Status

Accepted

## Context

Phase 1 model evaluation produced the following benchmark results:

| Model            | Precision | Recall | F1 Score |
| ---------------- | --------: | -----: | -------: |
| Isolation Forest |     0.796 |  0.775 |    0.786 |
| Random Forest    |     0.970 |  0.927 |    0.948 |

Following completion of model training and evaluation, concerns were raised regarding the validity and interpretability of these results.

Specifically:

* The reported metrics might be artificially inflated.
* Synthetic anomaly generation could be overly simplistic.
* Engineered features might introduce train-test leakage.
* One dominant feature might be responsible for most model decisions.
* Visual inspection of telemetry streams appeared inconsistent with the observed classification performance.

Before modifying the dataset, feature pipeline, or evaluation methodology, a technical audit was conducted to determine whether these concerns represented genuine defects or expected limitations of the current benchmark.

---

## Investigation

### 1. Train-Test Leakage Review

The training pipeline performs chronological splitting before any feature engineering is executed.

```text
Raw Dataset
    ↓
Chronological Split
    ↓
Independent Feature Engineering
    ↓
Model Training
    ↓
Model Evaluation
```

Additional validation confirmed:

* Training and testing datasets are processed independently.
* Rolling statistics are computed using historical observations only.
* No future observations are included in feature calculations.
* Labels are never incorporated into feature generation.
* Feature engineering is applied separately after the split.

### Additional Observation

The chronological split intentionally creates a more difficult evaluation scenario than random train-test shuffling.

Because future observations are completely withheld from training, evaluation metrics more closely approximate real deployment conditions where predictions must be generated against unseen future telemetry.

**Result:** No evidence of train-test leakage or methodological defects was identified.

---

### 2. Feature Importance Review

Random Forest feature importance analysis produced the following distribution:

| Feature                       | Importance |
| ----------------------------- | ---------: |
| conveyor_speed_z_score        |      0.300 |
| torque_z_score                |      0.268 |
| conveyor_speed_rate_of_change |      0.165 |
| torque_rate_of_change         |      0.103 |
| fill_level_z_score            |      0.073 |
| fill_level_rate_of_change     |      0.040 |
| torque_rolling_std            |      0.019 |
| conveyor_speed_rolling_std    |      0.019 |
| fill_level_rolling_std        |      0.013 |

### Observations

* Model performance is distributed across multiple engineered features.
* No single feature dominates prediction behavior.
* Conveyor speed and torque contribute most strongly to anomaly detection.
* Fill-level features provide meaningful but secondary predictive value.
* Multiple feature categories contribute to overall performance.

**Result:** Model performance cannot be attributed to a single trivial feature or shortcut.

---

### 3. Synthetic Benchmark Scope Review

The current synthetic dataset models a single anomaly family:

**Mechanical Conveyor Jam**

Expected effects include:

* Increased torque
* Reduced conveyor speed
* Reduced fill level

The simulator incorporates several realism mechanisms:

* Partial sensor activation
* Sensor-specific activation probabilities
* Magnitude jitter
* Temporal bleed effects
* Baseline operational noise

However, the dataset does not currently model:

* Sensor drift
* Long-term motor degradation
* Calibration faults
* Communication failures
* Multiple production lines
* Seasonal operating shifts
* Multiple anomaly classes

### Observations

The dataset is more sophisticated than a simple threshold-based anomaly simulation, but remains intentionally focused on a single fault family.

The resulting benchmark therefore evaluates performance on the modeled conveyor-jam scenario rather than arbitrary industrial failures.

**Result:** Dataset complexity is sufficient for Phase 1 model comparison, though broader generalization remains unverified.

---

## Decision

The existing synthetic dataset will be retained.

No dataset redesign, anomaly regeneration effort, or feature-pipeline restructuring will be performed during Phase 1.

The audit found no evidence of methodological defects sufficient to invalidate the reported evaluation metrics.

The project will proceed into Phase 2 using the current benchmark results as the established performance baseline.

### Scope Clarification

This decision does not claim that the current model is production-ready for arbitrary industrial environments.

It only establishes that:

* The evaluation methodology is technically sound.
* The benchmark results are reproducible.
* The feature-engineering pipeline functions correctly.
* The current dataset is sufficient for Phase 1 model comparison and architectural progression.

Generalization beyond the simulated conveyor-jam scenario remains outside the scope of the current benchmark.

---

## Consequences

### Positive

* Maintains project momentum.
* Preserves reproducible benchmark results.
* Allows focus to shift toward deployment and inference infrastructure.
* Metrics remain supported by leakage analysis and feature-importance review.
* Avoids unnecessary redesign without evidence of a technical defect.
* Establishes a stable baseline against which future dataset enhancements can be measured.

### Negative

The benchmark currently measures performance against only a single synthetic anomaly family.

Consequently:

* Generalization to unseen failure modes remains unverified.
* Performance against real-world industrial telemetry remains unknown.
* Future anomaly categories may require additional feature engineering or model retraining.

The benchmark should therefore be interpreted as:

> Performance on the simulated Mechanical Conveyor Jam scenario, not performance on arbitrary industrial anomalies.

---

## Future Work

Potential future dataset enhancements include:

1. Sensor drift anomalies.
2. Gradual motor wear anomalies.
3. Calibration offset faults.
4. Intermittent communication failures.
5. Multiple production lines.
6. Multi-class anomaly taxonomy.
7. Cross-line transfer-learning evaluation.
8. Long-term covariate drift simulation.
9. Seasonal operating pattern variation.

These enhancements are considered future improvements rather than blockers for continued architectural development.

---

## Rationale

The primary objective of Phase 1 was not to maximize simulation realism.

Instead, Phase 1 was designed to validate:

* The feature-engineering pipeline.
* The model-training workflow.
* The evaluation methodology.
* The model-selection process.
* The end-to-end machine learning architecture.

The review process identified legitimate limitations in benchmark scope but did not uncover evidence of:

* Data leakage.
* Feature leakage.
* Invalid evaluation methodology.
* Single-feature dominance.
* Artificial metric inflation.

Those objectives were successfully achieved.

Therefore, the current benchmark is considered technically sound for continuation into deployment-oriented phases without requiring immediate redesign of the synthetic dataset.
