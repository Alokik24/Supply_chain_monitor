import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def generate_data():
    # 1. Setup Parameters
    np.random.seed(42) # Ensures the "random" data is the same every time
    days = 90
    records = days * 24 * 60 # One record per minute
    start_time = datetime.now() - timedelta(days=days)
    
    print(f"Generating {records} records...")

    # 2. Create Timestamps
    timestamps = [start_time + timedelta(minutes=i) for i in range(records)]

    # 3. Generate Normal Sensor Values
    # Torque: Base 150 + small random noise
    torque = 150 + np.random.normal(0, 5, records)
    
    # Speed: Base 1200 + a slight sine wave for daily cycles
    time_indices = np.arange(records)
    speed = 1200 + (10 * np.sin(time_indices / 60)) + np.random.normal(0, 2, records)

    # 4. Inject Anomalies (5% of data)
    is_anomaly = np.zeros(records)
    anomaly_indices = np.random.choice(records, size=int(records * 0.05), replace=False)
    
    for idx in anomaly_indices:
        is_anomaly[idx] = 1
        # A "Jam" causes Torque to spike and Speed to crash
        torque[idx] += np.random.uniform(50, 100)
        speed[idx] -= np.random.uniform(300, 500)

    # 5. Save to CSV
    df = pd.DataFrame({
        'timestamp': timestamps,
        'torque': torque,
        'speed': speed,
        'is_anomaly': is_anomaly
    })
    
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/sensor_data.csv', index=False)
    print("Success! Data saved to data/sensor_data.csv")

if __name__ == "__main__":
    generate_data()