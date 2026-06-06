# data/generate.py
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def generate_hardware_wide_data():
    # 1. Setup Parameters for strict reproducibility
    np.random.seed(42) 
    days = 90
    records = days * 24 * 60 # 129,600 minutes total
    start_time = datetime.now() - timedelta(days=days)
    
    print(f"Generating {records} records matching ARCH-05")

    # 2. Create Timestamps
    timestamps = [start_time + timedelta(minutes=i) for i in range(records)]

    # 3. Generate Normal Sensor Values (Physics Base Profiles)
    torque = 150 + np.random.normal(0, 5, records)
    time_indices = np.arange(records)
    speed = 1200 + (10 * np.sin(time_indices / 60)) + np.random.normal(0, 2, records)
    # Adding the missing fill level baseline profile
    fill_level = 80 + np.random.normal(0, 1, records)

    # 4. Inject Anomalies (5% of data matching physical jam characteristics)
    is_anomaly = np.zeros(records)
    anomaly_indices = np.random.choice(records, size=int(records * 0.05), replace=False)
    
    for idx in anomaly_indices:
        is_anomaly[idx] = 1
        # Correlated Mechanical Jam physical symptoms:
        torque[idx] += np.random.uniform(50, 100)      # Motor strains hard
        speed[idx] -= np.random.uniform(300, 500)     # Conveyor belt slows down
        fill_level[idx] -= np.random.uniform(20, 40)   # Product splashes out / underfills

    # 5. Save to CSV including all hardware metadata attributes
    df = pd.DataFrame({
        'timestamp': timestamps,
        'line_id': 'Line_1', # Matches the tracking field in ARCH-05
        'torque': torque,
        'conveyor_speed': speed, # Named specifically to match ARCH-05 mappings
        'fill_level': fill_level, # Adding missing column
        'is_anomaly': is_anomaly
    })
    
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/sensor_data.csv', index=False)
    print("Success! Data saved with all 3 line types to data/sensor_data.csv.")

if __name__ == "__main__":
    generate_hardware_wide_data()