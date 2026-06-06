# ARCH-03: Model Evaluation Framework
Status: UPDATED — ALIGNED WITH 3-FEATURE PROFILE

## 1. Supervised vs. Unsupervised Anomaly Detection Strategy

Because our physical hardware emits three distinct streams simultaneously (`torque`, `conveyor_speed`, and `fill_level`), an anomaly is defined as a **multi-variable structural shift**. The `is_anomaly` column is generated to evaluate two separate modeling frameworks against this data footprint:

| Dimension | Supervised Learning (e.g., Random Forest Classifier) | Unsupervised Learning (e.g., Isolation Forest Engine) |
| :--- | :--- | :--- |
| **Role of `is_anomaly`** | Used directly during training as the explicit target variable label ($y$). | Hidden entirely during training. The model only reads features ($X$) to isolate outliers. Used strictly as a post-prediction validation baseline. |
| **Feature Interaction** | Maps exact, hard-coded boundary relationships across features (e.g., *If Speed drops AND Torque spikes AND Fill drops, trigger flag*). | Isomorphic splitting. It isolates observations that require fewer random attribute splits across the 3D feature space to separate them from dense, normal clusters. |
| **Core Advantage** | Extremely high precision and near-zero false alarms for the specific **Mechanical Conveyor Jam** failure profile it was trained on. | Highly adaptive. Can identify completely unmodeled failure modes (e.g., a slow fluid leak or motor degradation) because it detects any deviation from normal operational clusters. |
| **The Inherent Risk** | Completely blind to any new or shifting failure modes that do not look like our engineered training jam. | Higher initial rate of False Positives. May flag healthy, normal operational shifts (e.g., a deliberate line slow-down for a different product run) as anomalies. |

---

## 2. Contextual Evaluation Metrics

To grade our pipeline during Phase 1.3, we map our predictions against the ground-truth `is_anomaly` column using standard classification matrices:

* **Precision (The Operator Trust Metric):** $\frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}}$
  * *Factory Impact:* High precision prevents "alarm fatigue." If precision is low, operators will ignore the AI agent because it cries wolf on normal operations.
* **Recall (The Equipment Protection Metric):** $\frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}}$
  * *Factory Impact:* High recall ensures the system actually catches the conveyor jam before the mechanical motor snaps or spills liquid all over the factory floor.