import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient
import random
import time

# Material properties database
MATERIAL_PROFILES = {
    'Mild Steel': {'hardness': 120, 'thermal_conductivity': 50, 'specific_heat': 460},
    'Aluminum': {'hardness': 35, 'thermal_conductivity': 237, 'specific_heat': 900},
    'Wood': {'hardness': 2, 'thermal_conductivity': 0.12, 'specific_heat': 1700}
}

TOOL_WEAR_RATES = {
    'Mild Steel': 0.15,
    'Aluminum': 0.08,
    'Wood': 0.02
}

JOB_TYPES = ['turning', 'facing', 'threading', 'drilling', 'boring', 'knurling']

def calculate_machine_parameters(material, job_type, tool_diameter):
    """Calculate base parameters based on material and operation"""
    base_rpm = {
        'Mild Steel': random.randint(800, 1200),
        'Aluminum': random.randint(1500, 2500),
        'Wood': random.randint(2800, 3500)
    }[material]

    base_power = {
        'turning': 3.5,
        'facing': 4.0,
        'threading': 2.8,
        'drilling': 5.0,
        'boring': 3.0,
        'knurling': 2.5
    }[job_type] * (tool_diameter/10)

    return base_rpm, base_power

def ensure_collections_exist(db, lathe_id):
    """Ensure collections exist with proper indexes"""
    sensory_col = db[f"Lathe{lathe_id}.SensoryData"]
    job_col = db[f"Lathe{lathe_id}.JobDetails"]
    
    # Create indexes if they don't exist
    sensory_col.create_index([("timestamp", 1)])
    sensory_col.create_index([("JobID", 1)])
    job_col.create_index([("JobID", 1)], unique=True)
    
    return sensory_col, job_col

def generate_batch_sensor_data(lathe_id, job_id, duration, material, job_type, tool_no):
    """Generate all sensor data at once for testing"""
    try:
        # Connect to MongoDB with retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                client = MongoClient(
                    "mongodb://localhost:27017/lathe_monitoring",
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000
                )
                client.admin.command('ping')  # Test connection
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Connection failed (attempt {attempt + 1}), retrying...")
                time.sleep(retry_delay)
        
        db = client.get_database()
        
        # Ensure collections exist with indexes
        sensory_col, job_col = ensure_collections_exist(db, lathe_id)
        
        # Initialize job record
        job_record = {
            'JobID': job_id,
            'LatheID': lathe_id,
            'Material': material,
            'JobType': job_type,
            'ToolNo': tool_no,
            'StartTime': datetime.now(),
            'Status': 'Running',
            'FinalToolWear': 0
        }
        
        # Insert job record with error handling
        try:
            job_col.insert_one(job_record)
        except Exception as e:
            print(f"Error inserting job record: {e}")
            raise
        
        # Simulation parameters
        tool_diameter = 10 + tool_no * 2
        base_rpm, base_power = calculate_machine_parameters(material, job_type, tool_diameter)
        cooling_efficiency = 0.7
        ambient_temp = 25
        
        # Create time vector (data points every 5 seconds)
        n_points = int(duration * 60 / 5)
        elapsed_minutes = np.linspace(0, duration, n_points)
        
        # Tool wear progression
        tool_wear = np.minimum(
            100,
            TOOL_WEAR_RATES[material] * elapsed_minutes * np.random.normal(1, 0.05, n_points)
        )
        
        # RPM simulation
        rpm_noise = np.random.normal(0, 0.03, n_points)
        current_rpm = base_rpm * (1 - tool_wear/500) * (1 + rpm_noise)
        current_rpm = np.maximum(100, current_rpm)
        
        # Power simulation
        power_factor = 1 + (tool_wear/100) * 0.5
        power_noise = np.random.normal(0, 0.05, n_points)
        current_power = base_power * power_factor * (1 + power_noise)
        current_power = np.maximum(0.5, current_power)
        
        # Temperature simulation
        material_props = MATERIAL_PROFILES[material]
        heat_generation = current_power * 1000 * 0.8
        temp_increase = (heat_generation * elapsed_minutes * 60) / \
                      (material_props['specific_heat'] * material_props['hardness'])
        workpiece_temp = ambient_temp + temp_increase * (1 - cooling_efficiency)
        workpiece_temp = np.clip(workpiece_temp + np.random.normal(0, 2, n_points), ambient_temp, 300)
        
        # Vibration simulation
        vibration_base = {
            'Mild Steel': 2.5,
            'Aluminum': 1.8,
            'Wood': 0.8
        }[material]
        vibration = vibration_base * (current_rpm/1000) * (1 + tool_wear/50) * \
                   (1 + np.random.normal(0, 0.1, n_points))
        vibration = np.maximum(0, vibration)
        
        # Generate timestamps
        base_time = datetime.now()
        timestamps = [base_time + timedelta(seconds=5*i) for i in range(n_points)]
        
        # Create and insert documents in batches
        batch_size = 1000
        documents = [{
            'timestamp': ts,
            'JobID': job_id,
            'LatheID': lathe_id,
            'Material': material,
            'JobType': job_type,
            'ToolNo': tool_no,
            'Temperature': float(temp),
            'Vibration': float(vib),
            'RPM': float(rpm),
            'Power': float(pwr),
            'ToolWear': float(wear)
        } for ts, temp, vib, rpm, pwr, wear in zip(
            timestamps, workpiece_temp, vibration, current_rpm, current_power, tool_wear
        )]
        
        # Insert in batches to avoid overwhelming MongoDB
        inserted_count = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                result = sensory_col.insert_many(batch)
                inserted_count += len(result.inserted_ids)
            except Exception as e:
                print(f"Error inserting batch {i//batch_size + 1}: {e}")
                raise
        
        # Update job status
        update_result = job_col.update_one(
            {'JobID': job_id},
            {'$set': {
                'Status': 'Completed',
                'FinalToolWear': float(tool_wear[-1]),
                'EndTime': timestamps[-1]
            }}
        )
        
        return f"Successfully generated {inserted_count} data points for Job {job_id} (Lathe {lathe_id})"
    
    except Exception as e:
        return f"Error occurred: {str(e)}"
    finally:
        if 'client' in locals():
            client.close()

def generate_sample_data(num_lathes=10, jobs_per_lathe=2):
    """Generate sample data for multiple lathes"""
    materials = list(MATERIAL_PROFILES.keys())
    results = []
    
    for lathe_id in range(1, num_lathes + 1):
        for job_num in range(1, jobs_per_lathe + 1):
            job_id = f"JOB{lathe_id:02d}{job_num:02d}"
            material = random.choice(materials)
            job_type = random.choice(JOB_TYPES)
            tool_no = random.randint(1, 10)
            duration = random.uniform(5, 30)  # 5-30 minutes
            
            result = generate_batch_sensor_data(
                lathe_id=lathe_id,
                job_id=job_id,
                duration=duration,
                material=material,
                job_type=job_type,
                tool_no=tool_no
            )
            results.append(result)
            print(result)
    
    return results

if __name__ == "__main__":
    # Clear existing data
    client = MongoClient("mongodb://localhost:27017/lathe_monitoring")
    client.drop_database("lathe_monitoring")
    client.close()
    
    # Generate sample data
    generate_sample_data()
    
    # Verify data was inserted
    client = MongoClient("mongodb://localhost:27017/lathe_monitoring")
    try:
        print("\nDatabase Contents:")
        for coll in client.lathe_monitoring.list_collection_names():
            print(f"\nCollection: {coll}")
            count = client.lathe_monitoring[coll].count_documents({})
            print(f"Document count: {count}")
            if count > 0:
                print("Sample document:")
                print(client.lathe_monitoring[coll].find_one())
    finally:
        client.close()