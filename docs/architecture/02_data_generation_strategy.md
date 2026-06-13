# ARCH-02: Data Generation Strategy & Mathematical Profiles
Status: UPDATED — ALIGNED WITH 3-SENSOR PHYSICAL MODEL

## 1. Why Synthetic over Real Data?
1. **Edge Case Control:** Real-world manufacturing anomalies (like severe mechanical line jams) are rare in day-to-day operations. We intentionally inject these events at a strict **5% occurrence rate** to ensure our machine learning classifiers have a balanced distribution of failure cases to learn from during training.
2. **Deterministic Test Verification:** By establishing a hard pseudo-random anchor (`np.random.seed(42)`), we guarantee that every execution of our data layer produces identical matrix values. This eliminates data drift during local testing and allows for reproducible CI/CD pipeline runs.

---

## 2. The Multi-Sensor Mathematical Formula Profiles

Our physical data generator models an industrial Programmable Logic Controller (PLC) sampling three distinct mechanical and process attributes concurrently. Each sensor calculation builds on the base formula:

$$\text{Value}_t = \text{Baseline} + \text{Cyclic\_Component}_t + \text{Noise}_t$$

### A. Torque Stream ($T$)
Models the physical rotational force applied by the conveyor motor. It is stationary around its mean with standard measurement equipment variance.
* **Baseline ($\mu$):** $150\text{ Nm}$
* **Cyclic Component:** None ($0$)
* **Noise ($N$):** Gaussian White Noise sampled from $\mathcal{N}(\mu=0, \sigma=18)$

### B. Conveyor Speed Stream ($S$)
Models the physical linear velocity of the packaging line. It contains a diurnal sinusoidal pattern modeling natural factory temperature shifts and motor efficiency cycles throughout the day.
* **Baseline ($\mu$):** $1200\text{ RPM}$
* **Cyclic Component:** $10 \times \sin(\text{time\_index} / 60)$
* **Noise ($N$):** Gaussian White Noise sampled from $\mathcal{N}(\mu=0, \sigma=75)$

### C. Fill Level Stream ($F$)
Models the volume percentage of fluid successfully deposited into product containers. It is highly stable under normal operating conditions.
* **Baseline ($\mu$):** $80\%$
* **Cyclic Component:** None ($0$)
* **Noise ($N$):** Gaussian White Noise sampled from $\mathcal{N}(\mu=0, \sigma=9)$

---

## 3. Physical Anomaly Injection Modeling (The Conveyor Jam)

Anomalies are not injected as isolated random spikes. Instead, they simulate a **Correlated Physical Event** where all three data streams break normal statistical boundaries simultaneously to reveal a specific structural failure mode:

$$\text{If } t \in \text{Anomaly\_Indices} \implies \begin{cases} 
T_t = 150 + N_t + \mathcal{U}(50, 100) & \text{[Torque Spikes due to Motor Strain]} \\ 
S_t = 1200 + \text{Sin}_t + N_t - \mathcal{U}(300, 500) & \text{[Speed Drops due to Mechanical Friction]} \\ 
F_t = 80 + N_t - \mathcal{U}(20, 40) & \text{[Fill Level Drops due to Bottle Misalignment]} 
\end{cases}$$

Where $\mathcal{U}(\text{low}, \text{high})$ represents a Uniform Distribution draw, ensuring that every failure event introduces a severe deviation exceeding $3$ Standard Deviations from the baseline operational mean.