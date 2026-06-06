# ARCH-04: Synthetic Data Limitations & Assumptions
Status: APPROVED

Context: Physical Ingestion Modeling Constraints

## 1. The Reproducibility Mandate

This architecture enforces a strict pseudo-random tracking anchor via `np.random.seed(42)` at the entry point of the telemetry generation matrix (`data/generate.py`). 

### System Engineering Justification
Without a deterministic mathematical anchor, baseline data streams drift across generation execution runs, causing downstream data science verification metrics (Precision, Recall, F1-Score) to become moving targets. Securing a fixed mathematical seed allows for stable local testing and ensures that automated CI/CD model validation pipelines can evaluate code changes against a consistent, reliable data baseline.

---

## 2. Modeled Failure Modes vs. Real-World Gaps

Our physical dataset models a synchronized, multi-variable industrial phenomenon: a **Mechanical Conveyor Jam**. On the factory floor, this event breaks steady-state operational physics across three features simultaneously:
* **Torque Stream:** Suffers a uniform spike ($+50\text{ Nm}$ to $+100\text{ Nm}$) as the motor strains against physical resistance.
* **Conveyor Speed Stream:** Suffers a uniform drop ($-300\text{ RPM}$ to $-500\text{ RPM}$) due to increased friction.
* **Fill Level Stream:** Suffers a significant drop ($-20% \text{ to } -40%$) as container misalignment causes severe underfilling and liquid spillage under the active nozzles.

---

## 3. Scope Boundaries & Future Engineering Roadmaps

To keep the initial machine learning implementation focused and maintainable, the following real-world operational phenomena are explicitly out of scope for the current iteration:

### A. Sensor Dead-Lock (Flatlining)
* **The Reality:** A common hardware or firmware lockup where a transmitter freezes and constantly outputs an identical static value (*e.g.*, exactly $0.0\text{ RPM}$ or its last cached integer) over an extended timeline, completely eliminating natural ambient Gaussian noise.
* **Current Pipeline Impact:** Our baseline features look for variance shifts. A perfectly flat line introduces zero variance, which would bypass models looking for variance spikes until specialized signal-flatline filters are added to our feature engineering layer.

### B. Covariate Shift / Environmental Drift
* **The Reality:** The gradual, long-term degradation of physical components (such as bearing wear or belt stretching) that occurs over months or years. This pushes baseline operational means upward or downward in a slow, barely perceptible trend.
* **Current Pipeline Impact:** Because our synthetic baseline window spans 90 days with stable historical means, it does not simulate long-term statistical drift. In a live production system, this type of shift requires continuous model retraining cycles or adaptive threshold tuning to prevent false positive inflation over time.