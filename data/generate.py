# data/generate.py
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta


# ── Baseline noise standard deviations ────────────────────────────────────────
# These were calibrated empirically against the ARCH-02 anomaly injection ranges
# (torque: +50–100 Nm, speed: -300–500 RPM, fill: -20–40%) to produce a
# realistic classification difficulty where:
#   • Random Forest F1  ≈ 0.88–0.93  (high precision, some missed edge-case jams)
#   • Isolation Forest  ≈ 0.79–0.83  (solid unsupervised baseline with real FP rate)
#
# At the original σ values (5 / 2 / 1), anomaly spikes were 10–20σ events —
# trivially separable by any classifier and not representative of real plant noise.
# At these values, anomaly spikes are 3–6σ events with genuine class overlap at
# the low end of the injection magnitude range.
SIGMA_TORQUE = 18   # Nm   (was 5)
SIGMA_SPEED  = 75   # RPM  (was 2)
SIGMA_FILL   = 9    # %    (was 1)


def generate_hardware_wide_data():
    # ── 1. Reproducibility anchor (ARCH-04 §1) ────────────────────────────────
    np.random.seed(42)

    days    = 90
    records = days * 24 * 60          # 129,600 one-minute samples

    # Fixed wall-clock origin — datetime.now() drifts across reruns and breaks
    # any downstream test or notebook that expects stable timestamp values.
    start_time = datetime(2025, 9, 14, 0, 0, 0)

    print(f"Generating {records:,} records — ARCH-05 wide payload profile")

    # ── 2. Timestamps ─────────────────────────────────────────────────────────
    timestamps = [start_time + timedelta(minutes=i) for i in range(records)]

    # ── 3. Normal sensor baselines (ARCH-02 §2) ───────────────────────────────
    time_indices = np.arange(records)

    # Torque: stationary Gaussian, no cyclic component
    #   μ = 150 Nm
    torque = 150.0 + np.random.normal(0, SIGMA_TORQUE, records)

    # Conveyor speed: diurnal sinusoid models factory temperature / motor
    # efficiency cycles across the working day, plus Gaussian noise
    #   μ = 1200 RPM, sinusoid amplitude = 10 RPM, period ≈ 6.28 hr
    speed = (1200.0
             + (10.0 * np.sin(time_indices / 60.0))
             + np.random.normal(0, SIGMA_SPEED, records))

    # Fill level: highly stable under normal operating conditions
    #   μ = 80 %
    fill_level = 80.0 + np.random.normal(0, SIGMA_FILL, records)

    # ── 4. Anomaly injection — Mechanical Conveyor Jam (ARCH-02 §3) ───────────
    #
    # Physical model: a jam simultaneously stresses all three sensors.
    # Injection magnitudes are taken directly from the ARCH-02 uniform ranges:
    #   Torque   +50 – +100 Nm   (motor strains against physical resistance)
    #   Speed    -300 – -500 RPM (belt slows due to mechanical friction)
    #   Fill     -20 – -40 %     (bottle misalignment causes underfill / spillage)
    #
    # Realism layers added beyond a naive single-point spike:
    #   a) Partial-sensor firing  — each channel fires with independent probability,
    #      modelling real-world sensor lag and partial jam events.
    #   b) Magnitude jitter       — ±20% scale on every draw so severity varies,
    #      pushing low-magnitude events into the class boundary overlap zone.
    #   c) Temporal bleed         — the jam disturbs t+1 and t+2 at decaying
    #      intensity, matching the Echo Effect described in the EDA report §5.2.
    #      Bleed rows are intentionally NOT labelled is_anomaly=1: they are
    #      residual disturbances the model must tolerate without false-positiving.

    is_anomaly      = np.zeros(records, dtype=np.float32)
    n_anomalies     = int(records * 0.05)
    anomaly_indices = np.random.choice(records, size=n_anomalies, replace=False)

    P_TORQUE    = 0.85   # motor strain — almost always present in a jam
    P_SPEED     = 0.80   # belt slowdown — very common
    P_FILL      = 0.70   # underfill — slightly less tightly coupled
    BLEED_DECAY = [0.55, 0.25]  # t+1 retains 55%, t+2 retains 25% of spike

    for idx in anomaly_indices:
        is_anomaly[idx] = 1

        # Draw magnitudes from ARCH-02 §3 ranges, jittered ±20%
        torque_delta = np.random.uniform(50, 100) * np.random.uniform(0.80, 1.20)
        speed_delta  = np.random.uniform(300, 500) * np.random.uniform(0.80, 1.20)
        fill_delta   = np.random.uniform(20, 40)  * np.random.uniform(0.80, 1.20)

        # Independent Bernoulli channel activation
        fires_torque = np.random.rand() < P_TORQUE
        fires_speed  = np.random.rand() < P_SPEED
        fires_fill   = np.random.rand() < P_FILL
        if not (fires_torque or fires_speed or fires_fill):
            fires_torque = True  # guarantee at least one channel fires

        if fires_torque: torque[idx]     += torque_delta
        if fires_speed:  speed[idx]      -= speed_delta
        if fires_fill:   fill_level[idx] -= fill_delta

        # Temporal bleed — residual disturbance, not independent fault events
        for lag, decay in enumerate(BLEED_DECAY, start=1):
            bleed_idx = idx + lag
            if bleed_idx >= records:
                break
            if fires_torque: torque[bleed_idx]     += torque_delta * decay
            if fires_speed:  speed[bleed_idx]      -= speed_delta  * decay
            if fires_fill:   fill_level[bleed_idx] -= fill_delta   * decay

    # ── 5. Build DataFrame & persist ──────────────────────────────────────────
    df = pd.DataFrame({
        'timestamp':      timestamps,
        'line_id':        'Line_1',   # ARCH-05 tracking field
        'torque':         torque,
        'conveyor_speed': speed,       # column name matches ARCH-05 mapping table
        'fill_level':     fill_level,
        'is_anomaly':     is_anomaly,
    })

    os.makedirs('data', exist_ok=True)
    output_path = 'data/sensor_data.csv'
    df.to_csv(output_path, index=False)

    # ── 6. Verification summary ────────────────────────────────────────────────
    # Normal-only mask excludes bleed rows via a 2-minute forward window around
    # each anomaly event — bleed rows are labelled 0 but are physically disturbed
    # and would inflate the reported σ if included.
    anom_pos = set(np.where(is_anomaly == 1)[0])
    bleed_pos = set()
    for i in anom_pos:
        for lag in range(1, len(BLEED_DECAY) + 1):
            if i + lag < records:
                bleed_pos.add(i + lag)
    clean_indices = np.array([i for i in range(records)
                               if i not in anom_pos and i not in bleed_pos])

    actual_pct = is_anomaly.sum() / records * 100
    print(f"\n{'='*56}")
    print(f"  Records generated  : {records:,}")
    print(f"  Anomaly events     : {int(is_anomaly.sum()):,}  ({actual_pct:.2f}% of total)")
    print(f"  Bleed rows (excl.) : {len(bleed_pos):,}")
    print(f"  Output             : {output_path}")
    print(f"{'='*56}")
    print(f"\n  Clean baseline (anomaly + bleed rows excluded):")
    for col, lbl, sigma in [
        ('torque',        'Torque (Nm) ', SIGMA_TORQUE),
        ('conveyor_speed','Speed  (RPM)', SIGMA_SPEED),
        ('fill_level',    'Fill   (%)  ', SIGMA_FILL),
    ]:
        vals = df.loc[clean_indices, col]
        print(f"    {lbl}  μ={vals.mean():8.3f}   σ={vals.std():.3f}  "
              f"(design σ={sigma})")
    print()
    print("  Expected model performance (engineered features, no raw values):")
    print("    Random Forest    F1 ≈ 0.88 – 0.93")
    print("    Isolation Forest F1 ≈ 0.79 – 0.83")
    print()


if __name__ == "__main__":
    generate_hardware_wide_data()