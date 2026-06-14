# Developer Log: Phase 1.2 — Real-Time Feature Store Architecture

## The Core Problem Block
In this system, high-velocity supply chain sensors write raw event logs to PostgreSQL at a peak volume of 100 events per second. Our Isolation Forest machine learning model requires a rolling 30-minute statistical window (mean, standard deviation, and Z-score) to execute anomaly scoring on incoming telemetry data points. 

If the application attempts to compute these rolling metrics synchronously on the live ingestion path using heavy SQL aggregates or window functions over millions of raw historical database rows, the database CPU will saturate, leading to table deadlocks, connection timeouts, and pipeline failure.

## The Architecture Solution: Decoupling Compute from Serving
To solve this performance bottleneck, we implemented the M8 Feature Store Pattern by strictly decoupling our write path from our analytical execution loop:

### 1. The Hot Path (Fast Ingestion)
When a sensor submits data to `POST /readings`, the FastAPI backend performs zero mathematical computations. It validates the record schema via Pydantic, checks a composite natural idempotency key to block duplicate writes, appends the raw row to PostgreSQL, and instantly returns a `200 OK` response. This execution path takes less than 5 milliseconds.

### 2. The Cold Path (Asynchronous Feature Store)
Completely separate from the live ingestion pipeline, an isolated background worker process executes periodically. This worker runs an optimized database query using an index-backed SQL window function to pull only the warm history slice (the last-N records per sensor group). 

It feeds this minimal dataframe into `src/features.py` to compute vector transformations, then immediately flushes the updated metrics into a local Redis cache as a fast key-value store with a short Time-To-Live (TTL).

### 3. The Real-Time Scoring Loop
When the machine learning model runs inline inference, it bypasses PostgreSQL entirely. It reads the pre-computed 30-minute baseline metrics directly out of Redis memory in under 2 milliseconds, executes the model score, and flags anomalies safely without putting any read load on our transactional database tables.

## Technical Interview Q&A Breakdown

### Question:
"How do you serve machine learning features in real-time without constantly querying raw transactional database tables under high streaming load?"

### System Design Answer:
"You cannot query raw transactional tables on the hot path without risking query timeouts. To solve this, I implemented a decoupled Feature Store pattern. The ingestion path handles strict, append-only database writes. Concurrently, an asynchronous background pipeline periodically pulls a small history window slice from PostgreSQL, executes vector calculations via Pandas to derive the statistical baseline metrics (rolling means, standard deviations, and Z-scores), and updates an in-memory Redis cache. 

When the machine learning model requires feature vectors for inference, it pulls them directly out of Redis memory with a sub-2ms retrieval latency. This architecture isolates our core database write path from concurrent analytical read queries, allowing the ingestion platform to scale predictably."

### Strategic System Design Tradeoffs
* **Sacrifice Made:** We traded strict real-time data consistency for eventual consistency. Because the background feature calculation engine updates the cache in periodic batches, our rolling statistical averages may lag behind the live state by a few seconds. For industrial conveyor or asset tracking use cases, this brief propagation delay is completely acceptable.
* **Victory Gained:** We achieved total read-isolation on our primary database. No matter how many analytical queries or frontend dashboard nodes pull data from the platform, our core transactional write pipeline remains entirely unburdened.

# Developer Log: Phase 1.3 — Anomaly Detection Evaluation & Model Validation

## The Goal

With the feature engineering pipeline completed, the next objective was validating whether our anomaly detection architecture could actually distinguish normal conveyor operation from simulated mechanical failures.

This phase focused on answering three questions:

1. Do the engineered rolling-window features contain meaningful anomaly signals?
2. How does a supervised model compare against an unsupervised anomaly detector?
3. Can the evaluation pipeline be trusted, or is it accidentally benefiting from data leakage?

---

## Building a Leakage-Safe Evaluation Pipeline

One of the most common mistakes in time-series machine learning systems is allowing future information to leak into training data.

For example, if rolling averages are computed across the entire dataset before splitting into train and test partitions, future observations can influence historical feature values, producing unrealistically optimistic metrics.

To prevent this issue, the evaluation pipeline follows a strict chronological workflow:

```text
Raw Telemetry
      ↓
Chronological Split
      ↓
Independent Feature Engineering
      ↓
Model Training
      ↓
Evaluation
```

Train and test datasets never share rolling windows, statistical baselines, or historical context.

This design intentionally sacrifices a small amount of model performance in exchange for more realistic evaluation results.

---

## Model Selection Strategy

Two different anomaly detection approaches were evaluated.

### Isolation Forest (Unsupervised Baseline)

Isolation Forest was selected as the primary unsupervised benchmark because it aligns closely with how anomaly detection is often deployed in production environments.

In many industrial settings, large volumes of normal telemetry exist while labeled failure data is scarce.

Isolation Forest attempts to isolate unusual observations without requiring ground-truth labels.

Alternative approaches were considered:

#### DBSCAN

DBSCAN performs density-based clustering but struggles with continuously streaming telemetry and changing operating conditions. It also becomes computationally expensive as dataset size grows.

#### One-Class SVM

One-Class SVM can be effective on small datasets but scales poorly and is highly sensitive to hyperparameter selection. For a high-volume telemetry workload, it was not considered operationally practical.

Isolation Forest provided the best balance between scalability, interpretability, and operational realism.

---

### Random Forest (Supervised Benchmark)

Random Forest was used as a supervised comparison model.

Unlike Isolation Forest, it learns directly from labeled anomaly examples and can identify complex interactions between multiple sensor signals.

The expectation was straightforward:

> If labeled failure examples contain useful information, Random Forest should outperform the unsupervised baseline.

---

## What the Exploratory Analysis Revealed

Several findings emerged during exploratory analysis that were initially unexpected.

### 1. Fill Level Was Not the Dominant Signal

Early visual inspection suggested fill-level anomalies were highly separable from normal operation.

The initial hypothesis was that fill-level features would dominate model decisions.

Feature importance analysis revealed otherwise.

| Feature                       | Importance |
| ----------------------------- | ---------: |
| conveyor_speed_z_score        |      0.300 |
| torque_z_score                |      0.268 |
| conveyor_speed_rate_of_change |      0.165 |
| torque_rate_of_change         |      0.103 |
| fill_level_z_score            |      0.073 |
| fill_level_rate_of_change     |      0.040 |

The model relied primarily on speed and torque behavior rather than fill-level readings.

This was a useful reminder that visual intuition does not always match model behavior.

Rolling means and baseline-delta features were initially engineered
but ultimately excluded from the final model.

Feature importance analysis indicated that rolling volatility,
z-score normalization, and rate-of-change signals captured most
of the predictive information while reducing feature redundancy.

---

### 2. The Dataset Appeared Noisier Than Expected

Increasing baseline sensor variance initially created concern that the anomaly signal had become too weak.

However, feature importance analysis showed that engineered Z-scores and rate-of-change features successfully extracted useful information from noisy telemetry streams.

The model was not relying on a single obvious threshold.

Instead, it combined multiple weak signals into a stronger prediction.

---

### 3. High Performance Required Investigation

The Random Forest achieved significantly higher performance than expected.

Rather than accepting the results immediately, the evaluation pipeline was audited for:

* Train/test leakage
* Feature leakage
* Dominant-feature bias
* Improper rolling-window construction

No evidence of these issues was identified.

The most likely explanation is that the synthetic dataset contains a single well-defined anomaly family that remains learnable after feature engineering.

---

## Evaluation Results

| Model            | Precision | Recall | F1 Score |
| ---------------- | --------: | -----: | -------: |
| Isolation Forest |     0.796 |  0.775 |    0.786 |
| Random Forest    |     0.970 |  0.927 |    0.948 |

### Interpretation

The supervised Random Forest substantially outperformed the unsupervised Isolation Forest.

This result suggests that labeled anomaly examples contain significant predictive information beyond what unsupervised isolation techniques can capture.

The outcome aligns with expectations for industrial telemetry where fault signatures often manifest across multiple correlated sensors.

---

## Understanding Precision and Recall in a Factory Context

Machine-learning metrics are often discussed abstractly, but operational systems care about business consequences.

### False Positive

A false positive occurs when the system flags a healthy production line as anomalous.

Potential consequences:

* Unnecessary operator investigation
* Alert fatigue
* Reduced trust in the monitoring platform
* Temporary production interruption

### False Negative

A false negative occurs when a genuine conveyor jam is missed.

Potential consequences:

* Product waste
* Damaged equipment
* Unplanned downtime
* Delayed maintenance response

For industrial monitoring systems, false negatives are generally more expensive than false positives because missed failures can directly impact production output.

This explains why recall is particularly important when evaluating anomaly detection systems.

---

## Limitations

Despite encouraging results, several important limitations remain.

The current simulator models only one anomaly family:

* Conveyor jams
* Increased torque
* Reduced speed
* Reduced fill level

The evaluation does not currently test:

* Sensor drift
* Motor degradation
* Calibration failures
* Communication faults
* Multi-line behavior

Therefore, the benchmark should be interpreted as:

> Performance on a simulated conveyor-jam detection problem rather than performance on arbitrary industrial anomalies.

---

## Key Takeaway

The most important outcome of Phase 1.3 was not the Random Forest's F1 score.

It was establishing confidence that the evaluation pipeline itself was trustworthy.

By validating feature importance, auditing leakage risks, and comparing supervised and unsupervised approaches, the project now has a defensible baseline that can support future deployment and monitoring work in later phases.
