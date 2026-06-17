# Developer Log: Phase 1 — EDA, Feature Engineering & Model Validation

## Starting with the Dataset

Once the synthetic telemetry generator was complete, I wanted to understand whether the injected anomalies were actually visible in the data.

Rather than immediately training a model, I started with exploratory analysis.

The objective was to answer three questions:

- How do the sensors behave under normal operation?
- How do injected failures appear in the telemetry?
- Can abnormal behaviour be identified from raw measurements alone?

The initial analysis showed that anomaly periods affected multiple sensors simultaneously. Changes in conveyor speed were often accompanied by changes in torque and fill level, suggesting that anomalies were better represented as machine-state changes rather than isolated sensor failures.

At the same time, the raw values themselves were not always sufficient to separate normal and abnormal behaviour consistently.

This led me to investigate whether the recent history of a sensor contained more useful information than its current value.

---

## Engineering Context-Aware Features

The EDA suggested that anomaly signals often became clearer when a measurement was compared against its recent baseline.

Instead of using the raw sensor value directly, I began constructing features that captured local behaviour over time.

The feature pipeline included:

- Rolling means
- Rolling standard deviations
- Z-scores
- Rate-of-change metrics
- Baseline deviation measures

These features transformed individual telemetry readings into representations of machine behaviour rather than isolated measurements.

The resulting feature set provided a richer description of system state and became the foundation for the anomaly detection models.

The implementation details are documented separately in ADR-03 and ADR-06.

---

## Thinking About Real-Time Features

Once the feature engineering pipeline was working offline, a practical question appeared.

If these rolling statistics were useful for anomaly detection, how would they be generated in a real-time system?

My initial assumption was that the application could simply query PostgreSQL whenever a prediction was needed.

After tracing the execution path, it became clear that repeatedly calculating analytical features directly from historical telemetry would eventually place unnecessary load on the ingestion database.

This was my first exposure to the feature-store pattern.

Although I did not implement the complete architecture during this phase, the idea significantly influenced the system design decisions that would later appear in the ingestion and caching layers.

---

## Validating the Signals

The final objective was determining whether the engineered features actually improved anomaly detection performance.

Before comparing models, I focused on the evaluation process itself.

Because the dataset was time-series data, preventing leakage between training and testing periods was more important than achieving strong metrics.

After establishing a chronological train-test split, I evaluated two approaches:

- Isolation Forest
- Random Forest

Isolation Forest served as an unsupervised baseline, while Random Forest provided a supervised comparison using the anomaly labels available in the synthetic dataset.

The results confirmed that the engineered features contained meaningful anomaly signals and could be used effectively by both modelling approaches.

The detailed evaluation metrics, audit checks, and validation procedures are documented in ADR-06.

---

## Key Takeaways

At the beginning of this phase, I viewed anomaly detection primarily as a modelling problem.

By the end, I had a different perspective.

The quality of the features, the structure of the evaluation process, and the architecture required to serve those features were just as important as the model itself.

More importantly, this phase established the foundation for the ingestion pipeline and infrastructure work that followed in Phase 2.