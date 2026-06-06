# ARCH-02: Data Generation Strategy

## Why Synthetic over Real Data?
1. **Edge Case Control:** Real-world anomalies (like a motor exploding) are rare. We need to "inject" these intentionally (aiming for 5% of total data) to ensure our ML model actually has something to learn from.
2. **Deterministic Testing:** By using a "Seed" (a fixed starting point for randomness), we ensure that every time you run the script, you get the exact same "random" data. This makes our tests reproducible.

## The Mathematical Formulas
* **Normal Signal:** 

$Value = Baseline + (Amplitude \times \sin(Time)) + Noise$

* **Anomaly Injection:** We force specific rows to deviate by $> 3$ Standard Deviations from the Mean.