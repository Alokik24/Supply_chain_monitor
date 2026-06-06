# ARCH-03: Model Evaluation Framework

## Supervised vs. Unsupervised Anomaly Detection

In this system, we intentionally generate a binary label (`is_anomaly`) to support a dual-modeling strategy:

| Dimension | Supervised Learning (e.g., Random Forest) | Unsupervised Learning (e.g., Isolation Forest) |
| :--- | :--- | :--- |
| **Role of `is_anomaly`** | Used directly during training as the target variable ($y$). | Hidden during training; used strictly as a validation baseline. |
| **Core Advantage** | Highly accurate at catching known failure modes (like the specific mechanical jam we modeled). | Can detect entirely novel, unexpected failures because it only looks for deviations from normal clusters. |
| **The Risk** | Completely blind to new types of errors it hasn't explicitly seen in the training data. | Higher rate of False Positives (flagging normal, healthy operational shifts as anomalies). |