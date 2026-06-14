# ARCH-03: Model Evaluation Framework

Status: UPDATED — ALIGNED WITH FEATURE ENGINEERING & TEMPORAL VALIDATION

## 1. Supervised vs. Unsupervised Anomaly Detection Strategy

The anomaly monitor evaluates two fundamentally different detection paradigms against the same engineered telemetry feature space.

The synthetic data generator provides an `is_anomaly` ground-truth label representing a Mechanical Conveyor Jam event. This label enables direct comparison between supervised and unsupervised approaches.

| Dimension                | Supervised Learning (Random Forest Classifier)                                                                                                 | Unsupervised Learning (Isolation Forest)                                                                                                    |
| :----------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| **Role of `is_anomaly`** | Used directly during training as the target variable ($y$).                                                                                    | Hidden during training. Used only during post-training evaluation.                                                                          |
| **Learning Mechanism**   | Learns decision boundaries from labelled examples and captures non-linear interactions across engineered features.                             | Randomly partitions feature space and isolates observations requiring fewer splits, assigning higher anomaly scores to sparse observations. |
| **Core Advantage**       | High precision and low false-positive rates for the specific Mechanical Conveyor Jam profile represented in the training dataset.              | Can identify previously unseen operational deviations without requiring labelled examples.                                                  |
| **Primary Limitation**   | Performance depends on similarity between future failures and historical training patterns. Unseen failure modes may not be detected reliably. | Higher false-positive rates due to lack of explicit failure context. Normal operational shifts may occasionally be flagged as anomalies.    |
| **Operational Role**     | Primary production candidate when labelled training data is available.                                                                         | Baseline detector and fallback mechanism for unknown operational behaviors.                                                                 |

---

## 2. Temporal Evaluation Integrity

Telemetry observations exhibit temporal dependence and cannot be treated as independent records.

### The Leakage Risk

Random train-test shuffling allows future observations to influence model training, producing overly optimistic evaluation metrics that cannot be reproduced in production environments.

Because anomaly effects persist through temporal bleed and rolling-window feature calculations, random splits create a significant risk of information leakage.

### Evaluation Strategy

To preserve deployment realism:

* Historical observations are used for training.
* Future observations are reserved for testing.
* Feature engineering is applied independently to each split.
* No future information is allowed to influence training features.

This design ensures that evaluation metrics more accurately reflect real-world deployment behavior where predictions are always generated against unseen future observations.

---

## 2.1 Feature-Based Evaluation

Models are evaluated on engineered temporal features rather than raw sensor values alone.

The raw telemetry streams:

* Torque
* Conveyor Speed
* Fill Level

are transformed into statistical representations that capture short-term operational context.

### Candidate Feature Categories

#### Temporal Features

* Rolling Mean (30-minute windows)
* Rolling Standard Deviation (30-minute windows)
* Rate of Change

#### Statistical Features

* Z-Score
* Delta From Baseline

#### Cross-Sensor Relationships

* Torque / Conveyor Speed
* Torque × Fill Level
* Speed × Fill Level

### Engineering Rationale

The EDA phase demonstrated that anomaly effects persist beyond the labelled event due to temporal bleed. A single observation may therefore be insufficient to characterize system state.

Feature engineering converts raw telemetry into context-aware operational signals capable of capturing recovery behavior, volatility changes, and multi-sensor interactions.

---

## 3. Contextual Evaluation Metrics

Model performance is evaluated by comparing predictions against the ground-truth `is_anomaly` label.

### Precision (Operator Trust Metric)

Precision=\frac{TP}{TP+FP}

**Factory Impact**

Precision measures how often an alert is actually correct.

Low precision produces excessive false alarms, eventually causing operators to distrust or ignore anomaly notifications.

A high precision score indicates that flagged incidents are likely to represent genuine operational problems.

---

### Recall (Equipment Protection Metric)

Recall=\frac{TP}{TP+FN}

**Factory Impact**

Recall measures how many true failures are successfully detected.

Low recall allows genuine conveyor jams to pass through the monitoring layer undetected, increasing the likelihood of mechanical damage, product waste, or production downtime.

A high recall score indicates strong failure coverage.

---

### F1-Score (Balanced Detection Metric)

F1=2\cdot\frac{Precision\cdot Recall}{Precision+Recall}

**Factory Impact**

F1-Score balances operator trust and equipment protection.

A high F1 score indicates that the system achieves strong detection performance while maintaining acceptable false-positive rates.

Because anomaly monitoring requires both reliable detection and operational trust, F1 serves as the primary model selection metric.

---

## 4. Champion Model Selection Philosophy

Model selection is not based on accuracy alone.

Given the approximately 95:5 class distribution present in the synthetic dataset, accuracy can become misleading because a model that predicts every observation as normal would still achieve high accuracy.

The primary evaluation hierarchy is:

1. F1-Score
2. Precision
3. Recall
4. Operational Interpretability

The selected champion model must demonstrate:

* Strong detection capability
* Low false-positive rates
* Consistent performance on unseen future observations
* Compatibility with real-time deployment requirements

The winning model is serialized as:

```text
models/anomaly_detector.pkl
```

and becomes the inference engine used by the downstream scoring pipeline.
