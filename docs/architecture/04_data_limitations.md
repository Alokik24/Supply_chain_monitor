# ARCH-04: Synthetic Data Limitations & Assumptions

Status: APPROVED

Context: Physical Ingestion Modeling Constraints

## 1. Purpose

This Architecture Decision Record documents the known assumptions, simplifications, and modeling constraints of the synthetic telemetry generation pipeline.

The generated dataset is intentionally designed to model a controlled industrial anomaly detection environment rather than replicate the full operational complexity of a live manufacturing facility. These constraints are accepted to keep the initial machine learning pipeline reproducible, interpretable, and maintainable during early development phases.

---

## 2. Synthetic Data Scope Boundary

The current generator focuses on a single primary physical failure mode: a **Mechanical Conveyor Jam** affecting multiple sensor streams simultaneously.

While this event captures a realistic example of correlated industrial failures, it does not represent the complete range of operational faults that may occur in production environments.

Consequently, model performance measured against this dataset should be interpreted as performance against the simulated failure conditions rather than against all possible manufacturing anomalies.

---

## 3. Known Modeling Limitations

### A. Sensor Dead-Lock (Flatlining)

#### The Reality

Industrial sensors occasionally experience firmware lockups, communication faults, or hardware failures that cause a transmitter to repeatedly emit an identical value over an extended period of time.

Examples include:

* Constant `0 RPM`
* Repeated last-known measurement values
* Frozen sensor outputs despite changing physical conditions

#### Current Pipeline Impact

The current feature set is primarily designed around distributional deviations and correlated sensor behavior. Long-duration constant-value signals may require dedicated signal-quality monitoring features or specialized flatline detection logic that is currently outside the scope of the baseline implementation.

---

### B. Covariate Shift / Environmental Drift

#### The Reality

Manufacturing equipment naturally changes over time due to:

* Bearing wear
* Belt stretching
* Motor degradation
* Calibration drift
* Environmental changes

These effects gradually alter baseline operating characteristics across months or years.

#### Current Pipeline Impact

The synthetic dataset assumes stable statistical baselines throughout the entire 90-day observation period. Long-term drift behavior is not modeled.

A production deployment would likely require periodic retraining, adaptive thresholds, or online learning techniques to remain calibrated as operating conditions evolve.

---

### C. Single-Line Assumption

#### The Reality

Real manufacturing facilities frequently operate multiple production lines with differing characteristics.

Examples include:

* Machine-specific calibration offsets
* Equipment age differences
* Product-specific operating profiles
* Operator-dependent process variation

#### Current Pipeline Impact

The simulator generates telemetry for a single production line (`Line_1`) with stable operating characteristics.

Inter-line variability is intentionally excluded to keep anomaly behavior interpretable during early model development. Model performance observed on this dataset should not be assumed to generalize directly to heterogeneous multi-line environments.

---

### D. Missing Data & Communication Failures

#### The Reality

Industrial telemetry systems regularly encounter:

* Network interruptions
* Delayed packets
* Duplicate messages
* Missing observations
* Temporary sensor disconnects

These conditions often require specialized ingestion and recovery logic.

#### Current Pipeline Impact

The generator assumes perfect sensor availability and continuous data delivery.

All observations arrive in chronological order without packet loss, duplication, or transmission delays. As a result, the current dataset does not evaluate ingestion resilience under degraded infrastructure conditions.

---

### E. Sensor Calibration Error

#### The Reality

Sensors rarely remain perfectly calibrated throughout their operational lifetime.

Examples include:

* Offset drift
* Scale-factor inaccuracies
* Gradual measurement bias
* Component aging effects

These issues may create misleading measurements without producing obvious anomaly signatures.

#### Current Pipeline Impact

The simulator assumes all sensors remain correctly calibrated throughout the observation window.

Systematic measurement bias and calibration degradation are not currently modeled, meaning the anomaly pipeline is evaluated primarily against process anomalies rather than instrumentation faults.

---

## 4. Future Simulation Roadmap

Potential future enhancements include:

* Multi-line factory simulations
* Sensor flatline fault injection
* Missing-data generation
* Calibration drift modeling
* Seasonal and long-term covariate shift generation
* Additional anomaly classes beyond conveyor jams

These features were intentionally deferred to maintain a focused and explainable baseline dataset for early-stage anomaly detection experimentation.
