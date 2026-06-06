# ARCH-04: Synthetic Data Limitations & Assumptions
Status: REVIEWED

## 1. The Reproducibility Mandate
We enforce `np.random.seed(42)` at the entry point of data generation. Without a deterministic mathematical anchor, data science verification metrics (Precision, Recall, F1-Score) become moving targets, rendering automated CI/CD model validation impossible.

## 2. Modeled Failure Modes vs. Real-World Gaps
Our dataset currently models a single physical phenomenon: **Mechanical Conveyor Jams** (characterized by an inversely proportional relationship where Torque spikes and Speed drops).

### Current Out-of-Scope Failures:
* **Sensor Dead-Lock (Flatlining):** A hardware freeze where a sensor outputs a constant value (*e.g.*, exactly `0.0` speed) with zero Gaussian noise.
* **Covariate Shift / Environmental Drift:** Slow degradation of performance over months due to mechanical wear and tear, which pushes the baseline mean upward.