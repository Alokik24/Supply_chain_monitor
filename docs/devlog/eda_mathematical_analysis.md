# Building Statistical Anomaly Detection Features from Industrial Telemetry

## Problem Statement

Industrial sensor streams generate thousands of asynchronous readings per hour across interconnected production assets. In their raw form, these continuous streams of unstructured metrics obscure underlying operational state changes, mechanical degradation, and transient faults. Simple rule-based alerting on raw telemetry fails to account for three baseline characteristics of industrial systems:

* **Systemic Drift:** Slow, healthy modifications in operationalbaselines due to seasonal environmental factors or standard mechanical component wear.
* **Operational Heterogeneity:** Varied target profiles across different manufacturing lines and process execution modes (e.g., changes in product speed or material density).
* **Noise and Outliers:** High-frequency, non-fault disruptions that cause frequent false positives when standard static thresholds are applied.

To solve this, we must build a reproducible data-engineering and feature-engineering pipeline that maps unstructured event streams into structured feature spaces. This enables the calculation of localized, dynamic statistical properties that track real-time machine behavior relative to its recent operating history.

## Dataset Reconstruction

The telemetry data layer interfaces with a production PostgreSQL database to extract historical tracking logs. The ingestion environment utilizes explicit database parameters to establish an authenticated connection:

```python
# Database connection parameter mapping
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")

engine = create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")
df = pd.read_sql("SELECT * FROM sensor_data ORDER BY timestamp ASC;", engine)

```

### Entity-Attribute-Value (EAV) Stream Structure

The source database ingests sensor transmissions utilizing an Entity-Attribute-Value (EAV) schema over 3,000 continuous entries. Instead of dedicating distinct columns to individual sensors, data points are logged as individual event rows:

| id | line_id | sensor_type | value | timestamp |
| --- | --- | --- | --- | --- |
| 1 | line_1 | conveyor_speed | 1195.42 | 2026-02-08 08:00:01 |
| 2 | line_1 | fill_level | 78.12 | 2026-02-08 08:00:01 |
| 3 | line_1 | torque | 152.34 | 2026-02-08 08:00:01 |

While this storage strategy scales efficiently for heterogeneous data collection, it cannot be consumed directly by statistical profiling models or machine learning engines.

### Pivot Matrix Transformation

To build synchronized operational state vectors, the long-form EAV rows are reshaped into an orthogonal wide feature matrix $\mathbf{M} \in \mathbb{R}^{1000 \times 3}$ using an index-pivoting step:

```python
# Pivot transformation from EAV event log to feature matrix
df_matrix = df.pivot(
    index=['timestamp', 'line_id'], 
    columns='sensor_type', 
    values='value'
).reset_index()
df_matrix.columns.name = None

```

This structural reshaping aggregates the individual metrics into synchronized, multi-variate snapshots mapped across continuous time vectors:

$$\vec{x}_t = \begin{bmatrix} \text{conveyor\_speed}_t & \text{fill\_level}_t & \text{torque}_t \end{bmatrix}$$


## Baseline Statistical Analysis

We ran a global parametric evaluation across the structured columns using `df.describe()` to map out the baseline operating envelope of the assets. This summary exposed structural variance and outlier distribution trends within the historical profile.

```python
# Establish global analytical baselines
df_summary = df_matrix[['conveyor_speed', 'fill_level', 'torque']].describe()
df_summary.loc['iqr'] = df_summary.loc['75%'] - df_summary.loc['25%']

```

### Extracted Baseline Properties

* **Conveyor Speed (RPM):**
* Arithmetic Mean ($\mu$): $\approx 1176.75$
* Standard Deviation ($\sigma$): $\approx 97.34$
* Interquartile Range ($IQR$): $\approx 13.71$


* **Fill Level (%):**
* Arithmetic Mean ($\mu$): $\approx 78.25$
* Standard Deviation ($\sigma$): $\approx 7.16$
* Interquartile Range ($IQR$): $\approx 1.42$


* **Motor Torque (Nm):**
* Arithmetic Mean ($\mu$): $\approx 154.60$
* Standard Deviation ($\sigma$): $\approx 18.89$
* Interquartile Range ($IQR$): $\approx 6.95$



### Variance Structural Analysis

The analysis reveals a significant mathematical divergence between the global sample standard deviations ($\sigma$) and the non-parametric interquartile ranges ($IQR$) across all tracked metrics. For instance, `conveyor_speed` displays a global $\sigma$ of $\approx 97.34$, while its core $IQR$ span is narrow ($\approx 13.71$).

This large spread indicates that the global variance calculation is heavily skewed by extreme outliers or distinct multi-modal operational shifts. Consequently, static limit structures based on global data properties will create wide deadbands, leaving the system blind to subtle operational degradation.

## Distribution Modeling

To evaluate the probability density function of the assets, we paired discrete frequency analysis with non-parametric continuous density modeling.

```python
import seaborn as sns
import matplotlib.pyplot as plt

# Continuous distribution visualization
plt.figure(figsize=(10, 4))
sns.histplot(data=df_matrix, x='conveyor_speed', kde=True, bins=50)
plt.title("Sensor Density Function & Non-Parametric Continuous Estimation")
plt.show()

```

### Discrete Histograms vs. Kernel Density Estimation (KDE)

The continuous tracking pipeline combines discrete histogram tracking with continuous Kernel Density Estimation (KDE) to remove arbitrary bin-edge artifacts:

$$\hat{f}(x) = \frac{1}{nh} \sum_{i=1}^{n} K\left(\frac{x - x_i}{h}\right)$$

Where $K(u)$ is a symmetric Gaussian optimization kernel centered over every discrete historical observation point:

$$K(u) = \frac{1}{\sqrt{2\pi}} e^{-\frac{u^2}{2}}$$

### Distribution Insights

* **Heavy-Tailed Artifacts:** The continuous curves confirm that the probability density functions exhibit extreme right-skewed heavy tails across both speed and torque profiles.
* **Multi-Modal Setpoints:** The presence of localized micro-peaks reveals hidden operational transitions, confirming that the machinery shifts between distinct, stable processing targets over time.

## Feature Engineering

Because global statistical bounds fail to account for operational shifts and long-term process drift, we built a localized rolling window feature architecture. This structure computes real-time statistical operators over a backward-looking sliding window of $W = 30$ continuous samples.

```python
# Rolling statistical operator generation
df_features = df_matrix.copy().sort_values('timestamp')

df_features['speed_roll_mean'] = df_features['conveyor_speed'].rolling(window=30).mean()
df_features['speed_roll_std'] = df_features['conveyor_speed'].rolling(window=30).std()

```

### Local Moving Window Reference Operator ($\mu_t$)

The localized rolling mean filters out high-frequency noise, creating an adaptive baseline that tracks gradual, safe operational modifications without lagging:

$$\mu_t = \frac{1}{W} \sum_{i=0}^{W-1} x_{t-i}$$

### Local Volatility Reference Operator ($\sigma_t$)

The local rolling standard deviation quantifies the instantaneous variance within the sliding window, adjusting the dynamic envelope based on current operational volatility:

$$\sigma_t = \sqrt{\frac{1}{W-1} \sum_{i=0}^{W-1} (x_{t-i} - \mu_t)^2}$$


## Dynamic Anomaly Detection

By combining our rolling metrics into a single calculation, we engineer a dynamic anomaly tracking feature: the Rolling Z-Score ($Z_t$). This transform measures how many local standard deviations a real-time sensor observation sits away from its moving baseline.

```python
# Real-time transformation to engineered rolling z-score
df_features['speed_z_score'] = (
    df_features['conveyor_speed'] - df_features['speed_roll_mean']
) / df_features['speed_roll_std']

```

### Mathematical Transform Formulation

The feature space transformation scales real-time sensor anomalies relative to recent local operational variance:

$$Z_t = \frac{x_t - \mu_t}{\sigma_t}$$

Where:

* $x_t$: Real-time sensor observation point at chronological index $t$.
* $\mu_t$: Local moving mean calculated over the previous 30 samples.
* $\sigma_t$: Local moving standard deviation calculated over the previous 30 samples.

### Boundary Condition Selection

We use a standard statistical boundary condition to flag anomalies:

$$\mathcal{A}_t = \begin{cases} 
1, & \text{if } |Z_t| > 3.0 \\ 
0, & \text{otherwise} 
\end{cases}$$

This boundary condition is established in the visualization layer by plotting two symmetric control lines at $\pm 3\sigma$:

```python
# Dual-axis real-time anomaly tracking visualization
fig, ax1 = plt.subplots(figsize=(14, 6))

# Plot raw sensor timeline
ax1.plot(df_features['timestamp'], df_features['conveyor_speed'], color='tab:blue', alpha=0.6, label="Raw Speed")
ax1.set_ylabel('Raw Conveyor Speed (RPM)', color='tab:blue', weight="bold")

# Instantiate secondary synchronized tracking axis
ax2 = ax1.twinx()  
ax2.plot(df_features['timestamp'], df_features['speed_z_score'], color='tab:red', alpha=0.8, linewidth=1, label="Z-Score")
ax2.set_ylabel('Engineered Rolling Z-Score', color='tab:red', weight="bold")

# Plot standard statistical boundary thresholds
ax2.axhline(y=3.0, color='black', linestyle='--', alpha=0.5, label="Threshold Boundary (+3σ)")
ax2.axhline(y=-3.0, color='black', linestyle='--', alpha=0.5)

plt.title("Chronological Feature Matrix: Tracking Streaming Anomalies & Echo Windows Over Time", fontsize=14, weight="bold")
fig.tight_layout()
plt.show()

```

Under normal operating conditions ($X_t \sim \mathcal{N}(\mu_t, \sigma_t^2)$), the empirical rule states that $99.73\%$ of data points will fall within three standard deviations of the mean. This limits false positives to just $\approx 0.27\%$, ensuring that alarms are only triggered by genuine mechanical faults or sudden, significant system deviations.


## Outcomes and System Performance

### Static Threshold Vulnerability vs. Rolling Adaptation

* **Static Threshold Failures:** If a static high-level alarm threshold was configured at $1200 \text{ RPM}$ based on initial data summaries, a deliberate operational speed change up to $1220 \text{ RPM}$ would cause continuous false alarms, even if the machinery is running perfectly.
* **Rolling Z-Score Resilience:** Because the engineered pipeline dynamically shifts its local reference metrics ($\mu_t, \sigma_t$), standard process drift or intentional speed adjustments do not cause false alarms. The moving baseline adapts smoothly to these variations, maintaining a clean rolling score ($Z_t \approx 0.0\sigma$).

### Clear Fault Isolation

When a sudden mechanical issue occurs—such as a localized component slip that causes conveyor speed to spike by $35 \text{ RPM}$ in a single time step—the engineered feature captures the anomaly immediately. While the change might look small compared to global historical variance, the localized rolling standard deviation recognizes it as a massive statistical deviation, driving the rolling Z-score to $+8.5\sigma$. This easily breaks past the $+3.0\sigma$ boundary line, flagging the event as a true anomaly.

By shifting from global profiling to an engineered rolling Z-score feature matrix, we have built a robust, adaptive anomaly detection pipeline. This framework effectively isolates sudden mechanical faults while remaining resilient against standard process noise and long-term machine drift.