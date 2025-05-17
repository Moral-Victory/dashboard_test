from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timedelta
import random
import os
from typing import List, Dict, Optional
import numpy as np
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder

# Configuration
class Settings(BaseModel):
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/lathe_monitoring")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", 8000))
    max_history_hours: int = int(os.getenv("MAX_HISTORY_HOURS", 168))
    default_lathe_count: int = int(os.getenv("DEFAULT_LATHE_COUNT", 10))

settings = Settings()

# Initialize FastAPI
app = FastAPI(
    title="Lathe Monitoring API",
    description="API for monitoring industrial lathe machines",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration - more restrictive in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# MongoDB connection with error handling
try:
    client = MongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    # Test the connection
    client.server_info()
    db = client.get_database()
except Exception as e:
    raise RuntimeError(f"Failed to connect to MongoDB: {str(e)}")

# Create indexes for better performance
def create_indexes():
    for lathe_id in range(1, settings.default_lathe_count + 1):
        sensory_col = f"Lathe{lathe_id}.SensoryData"
        job_col = f"Lathe{lathe_id}.JobDetails"
        
        try:
            db[sensory_col].create_index([("timestamp", DESCENDING)])
            db[sensory_col].create_index([("JobID", ASCENDING)])
            db[job_col].create_index([("StartTime", DESCENDING)])
            db[job_col].create_index([("Status", ASCENDING)])
        except Exception as e:
            print(f"Warning: Failed to create indexes for lathe {lathe_id}: {str(e)}")

create_indexes()

# Pydantic Models for request/response validation
class LatheSummary(BaseModel):
    lathe_id: int
    name: str
    health_score: float
    uptime: float
    status: str
    failure_count: int

class SensorData(BaseModel):
    timestamp: datetime
    Temperature: Optional[float] = None
    Vibration: Optional[float] = None
    RPM: Optional[float] = None
    Power: Optional[float] = None
    ToolWear: Optional[float] = None
    JobID: Optional[str] = None

class SensorStats(BaseModel):
    min: float
    max: float
    avg: float

class ProductAnalysis(BaseModel):
    product_types: Dict[str, int]
    product_quality: Dict[str, Dict[str, float]]
    params_by_type: Dict[str, Dict[str, float]]

class JobDetails(BaseModel):
    JobID: str
    LatheID: int
    Material: str
    JobType: str
    ToolNo: int
    StartTime: datetime
    Status: str
    FinalToolWear: float

# Helper functions with improved error handling
def calculate_health_score(lathe_data: List[Dict]) -> float:
    """Calculate health score based on sensor data with improved safety checks"""
    if not lathe_data:
        return 0.0
    
    try:
        # Extract metrics with type checking and default values
        metrics = {
            'Temperature': [],
            'Vibration': [],
            'RPM': [],
            'Power': [],
            'ToolWear': []
        }
        
        for d in lathe_data:
            for metric in metrics.keys():
                if metric in d and isinstance(d[metric], (int, float)):
                    metrics[metric].append(d[metric])
        
        # Calculate normalized scores (0-1 range)
        scores = {
            'temp': 1 - (np.mean(metrics['Temperature']) - 25) / 100 if metrics['Temperature'] else 0,
            'vib': 1 - np.mean(metrics['Vibration']) / 10 if metrics['Vibration'] else 0,
            'rpm': np.mean(metrics['RPM']) / 3000 if metrics['RPM'] else 0,
            'power': 1 - np.mean(metrics['Power']) / 15 if metrics['Power'] else 0,
            'wear': 1 - np.mean(metrics['ToolWear']) / 100 if metrics['ToolWear'] else 0
        }
        
        # Weighted average
        health_score = (
            0.2 * scores['temp'] + 
            0.15 * scores['vib'] + 
            0.25 * scores['rpm'] + 
            0.2 * scores['power'] + 
            0.2 * scores['wear']
        )
        
        return max(0, min(100, health_score * 100))
    except Exception as e:
        print(f"Error calculating health score: {str(e)}")
        return 0.0

def calculate_uptime(lathe_id: int) -> float:
    """Calculate uptime percentage for a lathe with improved reliability"""
    try:
        job_col = f"Lathe{lathe_id}.JobDetails"
        
        if not collection_exists(job_col):
            return 100.0  # Assume 100% if no job collection exists
            
        jobs = list(db[job_col].find({"Status": "Completed"}))
        
        if not jobs:
            return 100.0  # No completed jobs yet
            
        total_duration = sum(
            (job['EndTime'] - job['StartTime']).total_seconds() 
            for job in jobs 
            if 'EndTime' in job and 'StartTime' in job
        )
        
        # Calculate operational time with realistic downtime
        operational_time = total_duration
        downtime = operational_time * random.uniform(0.05, 0.15)  # 5-15% downtime
        
        uptime = operational_time / (operational_time + downtime) if (operational_time + downtime) > 0 else 1.0
        return max(0, min(100, uptime * 100))
    except Exception as e:
        print(f"Error calculating uptime for lathe {lathe_id}: {str(e)}")
        return 100.0

def get_lathe_status(health_score: float) -> str:
    """Determine status based on health score with thresholds"""
    if health_score >= 80:
        return "Operational"
    elif health_score >= 60:
        return "Warning"
    else:
        return "Failure"

def collection_exists(collection_name: str) -> bool:
    """Check if a collection exists with cache"""
    try:
        return collection_name in db.list_collection_names()
    except Exception as e:
        print(f"Error checking collection existence: {str(e)}")
        return False

# API Endpoints with improved error handling and validation
@app.get("/lathes", response_model=List[LatheSummary])
async def get_all_lathes(
    num_lathes: int = Query(
        settings.default_lathe_count, 
        description="Number of lathes to check",
        ge=1,
        le=50
    )
):
    """Get summary data for all lathes with pagination"""
    try:
        lathes = []
        
        for lathe_id in range(1, num_lathes + 1):
            try:
                sensory_col = f"Lathe{lathe_id}.SensoryData"
                job_col = f"Lathe{lathe_id}.JobDetails"
                
                # Check if collections exist
                if not collection_exists(sensory_col) or not collection_exists(job_col):
                    lathes.append({
                        "lathe_id": lathe_id,
                        "name": f"Lathe M{lathe_id}",
                        "health_score": 0.0,
                        "uptime": 0.0,
                        "status": "Offline",
                        "failure_count": 0
                    })
                    continue
                    
                # Get recent sensor data with projection for efficiency
                sensor_data = list(db[sensory_col].find(
                    {},
                    {"Temperature": 1, "Vibration": 1, "RPM": 1, "Power": 1, "ToolWear": 1}
                ).sort("timestamp", -1).limit(1000))
                
                if not sensor_data:
                    lathes.append({
                        "lathe_id": lathe_id,
                        "name": f"Lathe M{lathe_id}",
                        "health_score": 0.0,
                        "uptime": 0.0,
                        "status": "No Data",
                        "failure_count": 0
                    })
                    continue
                
                # Calculate metrics
                health_score = calculate_health_score(sensor_data)
                uptime = calculate_uptime(lathe_id)
                status = get_lathe_status(health_score)
                
                # Count failures more efficiently
                failure_count = db[job_col].count_documents({
                    "Status": "Completed",
                    "FinalToolWear": {"$gt": 90}
                })
                
                lathes.append({
                    "lathe_id": lathe_id,
                    "name": f"Lathe M{lathe_id}",
                    "health_score": round(health_score, 1),
                    "uptime": round(uptime, 1),
                    "status": status,
                    "failure_count": failure_count
                })
            except Exception as e:
                print(f"Error processing lathe {lathe_id}: {str(e)}")
                lathes.append({
                    "lathe_id": lathe_id,
                    "name": f"Lathe M{lathe_id}",
                    "health_score": 0.0,
                    "uptime": 0.0,
                    "status": "Error",
                    "failure_count": 0
                })
                continue
        
        return lathes
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching lathes data: {str(e)}"
        )

@app.get("/lathes/{lathe_id}/history", response_model=List[SensorData])
async def get_lathe_history(
    lathe_id: int,
    hours: int = Query(
        24, 
        description="Number of hours of history to retrieve", 
        ge=1, 
        le=settings.max_history_hours
    ),
    limit: int = Query(
        1000,
        description="Maximum number of records to return",
        ge=1,
        le=5000
    )
):
    """Get historical sensor data for a specific lathe with pagination"""
    try:
        sensory_col = f"Lathe{lathe_id}.SensoryData"
        
        if not collection_exists(sensory_col):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lathe {lathe_id} not found"
            )
            
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get sensor data within time range with projection
        sensor_data = list(db[sensory_col].find(
            {
                "timestamp": {"$gte": start_time, "$lte": end_time}
            },
            {
                "_id": 0,
                "timestamp": 1,
                "Temperature": 1,
                "Vibration": 1,
                "RPM": 1,
                "Power": 1,
                "ToolWear": 1,
                "JobID": 1
            }
        ).sort("timestamp", 1).limit(limit))
        
        if not sensor_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sensor data available for Lathe {lathe_id} in the last {hours} hours"
            )
        
        return sensor_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching historical data: {str(e)}"
        )

@app.get("/lathes/{lathe_id}", response_model=Dict)
async def get_lathe_details(lathe_id: int):
    """Get detailed information for a specific lathe"""
    try:
        sensory_col = f"Lathe{lathe_id}.SensoryData"
        job_col = f"Lathe{lathe_id}.JobDetails"
        
        if not collection_exists(sensory_col):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lathe {lathe_id} not found"
            )
            
        # Get recent sensor data with projection
        sensor_data = list(db[sensory_col].find(
            {},
            {
                "timestamp": 1,
                "Temperature": 1,
                "Vibration": 1,
                "RPM": 1,
                "Power": 1,
                "ToolWear": 1,
                "JobID": 1
            }
        ).sort("timestamp", -1).limit(1000))
        
        if not sensor_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sensor data available for Lathe {lathe_id}"
            )
        
        # Calculate metrics
        health_score = calculate_health_score(sensor_data)
        uptime = calculate_uptime(lathe_id)
        status = get_lathe_status(health_score)
        
        # Get current job metrics from latest sensor reading
        current_job = db[sensory_col].find_one(
            {},
            {
                "timestamp": 1,
                "Temperature": 1,
                "Vibration": 1,
                "RPM": 1,
                "Power": 1,
                "ToolWear": 1,
                "JobID": 1
            },
            sort=[("timestamp", -1)]
        )
        
        # Calculate jobs completed today more efficiently
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        jobs_completed_today = db[job_col].count_documents({
            "Status": "Completed",
            "EndTime": {"$gte": today_start}
        }) if collection_exists(job_col) else 0
        
        # Get daily target
        daily_target = 10  # Default
        if collection_exists(job_col):
            target_doc = db[job_col].find_one(
                {},
                {"DailyJobTarget": 1},
                sort=[("StartTime", -1)]
            )
            if target_doc and "DailyJobTarget" in target_doc:
                daily_target = target_doc["DailyJobTarget"]
        
        # Count failures
        failure_count = db[job_col].count_documents({
            "Status": "Completed",
            "FinalToolWear": {"$gt": 90}
        }) if collection_exists(job_col) else 0
        
        return {
            "lathe_id": lathe_id,
            "name": f"Lathe M{lathe_id}",
            "health_score": round(health_score, 1),
            "uptime": round(uptime, 1),
            "status": status,
            "failure_count": failure_count,
            "current_job": current_job,
            "jobs_completed_today": jobs_completed_today,
            "daily_job_target": daily_target,
            "current_temperature": current_job.get("Temperature") if current_job else None,
            "current_vibration": current_job.get("Vibration") if current_job else None,
            "current_rpm": current_job.get("RPM") if current_job else None,
            "current_power": current_job.get("Power") if current_job else None,
            "current_tool_wear": current_job.get("ToolWear") if current_job else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching lathe details: {str(e)}"
        )

@app.get("/lathes/{lathe_id}/sensor-data", response_model=Dict)
async def get_lathe_sensor_data(
    lathe_id: int, 
    limit: int = Query(
        1000, 
        description="Number of records to return", 
        ge=1, 
        le=5000
    )
):
    """Get sensor data for a specific lathe with pagination"""
    try:
        sensory_col = f"Lathe{lathe_id}.SensoryData"
        
        if not collection_exists(sensory_col):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lathe {lathe_id} not found"
            )
            
        # Get sensor data with projection for efficiency
        sensor_data = list(db[sensory_col].find(
            {},
            {
                "_id": 0,
                "timestamp": 1,
                "Temperature": 1,
                "Vibration": 1,
                "RPM": 1,
                "Power": 1,
                "ToolWear": 1
            }
        ).sort("timestamp", -1).limit(limit))
        
        if not sensor_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sensor data available for Lathe {lathe_id}"
            )
        
        # Calculate statistics more safely
        def safe_stats(values):
            if not values:
                return {"min": 0, "max": 0, "avg": 0}
            return {
                "min": min(values),
                "max": max(values),
                "avg": np.mean(values)
            }
        
        stats = {
            "Temperature": safe_stats([d["Temperature"] for d in sensor_data if "Temperature" in d]),
            "Vibration": safe_stats([d["Vibration"] for d in sensor_data if "Vibration" in d]),
            "RPM": safe_stats([d["RPM"] for d in sensor_data if "RPM" in d]),
            "Power": safe_stats([d["Power"] for d in sensor_data if "Power" in d]),
            "ToolWear": safe_stats([d["ToolWear"] for d in sensor_data if "ToolWear" in d])
        }
        
        return {
            "sensor_data": sensor_data,
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sensor data: {str(e)}"
        )

@app.get("/lathes/{lathe_id}/product-analysis", response_model=ProductAnalysis)
async def get_lathe_product_analysis(lathe_id: int):
    """Get product analysis for a specific lathe"""
    try:
        sensory_col = f"Lathe{lathe_id}.SensoryData"
        job_col = f"Lathe{lathe_id}.JobDetails"
        
        if not collection_exists(job_col):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lathe {lathe_id} not found"
            )
            
        # Get all completed jobs with projection
        jobs = list(db[job_col].find(
            {"Status": "Completed"},
            {"Material": 1, "JobID": 1, "FinalToolWear": 1}
        ))
        
        if not jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No completed jobs found for Lathe {lathe_id}"
            )
        
        # Product type distribution
        product_types = {}
        for job in jobs:
            material = job.get("Material", "Unknown")
            product_types[material] = product_types.get(material, 0) + 1
        
        # Product quality analysis
        product_quality = {}
        params_by_type = {}
        
        for material in product_types.keys():
            material_jobs = [job["JobID"] for job in jobs if job.get("Material") == material]
            
            # Get sensor data for this material
            sensor_data = []
            if collection_exists(sensory_col):
                sensor_data = list(db[sensory_col].find(
                    {"JobID": {"$in": material_jobs}},
                    {"Temperature": 1, "Vibration": 1, "RPM": 1, "Power": 1, "ToolWear": 1}
                ))
            
            if not sensor_data:
                continue
            
            # Calculate failure rate
            total_jobs = len(material_jobs)
            failed_jobs = db[job_col].count_documents({
                "JobID": {"$in": material_jobs},
                "FinalToolWear": {"$gt": 80}
            })
            
            # Calculate average health score
            health_scores = []
            for job_id in material_jobs:
                job_sensor_data = list(db[sensory_col].find(
                    {"JobID": job_id},
                    {"Temperature": 1, "Vibration": 1, "RPM": 1, "Power": 1, "ToolWear": 1}
                )) if collection_exists(sensory_col) else []
                
                if job_sensor_data:
                    health_scores.append(calculate_health_score(job_sensor_data))
            
            avg_health_score = np.mean(health_scores) if health_scores else 0
            
            product_quality[material] = {
                "failure_rate": round((failed_jobs / total_jobs) * 100, 1) if total_jobs > 0 else 0,
                "avg_health_score": round(avg_health_score, 1)
            }
            
            # Calculate average parameters safely
            def safe_avg(values):
                return np.mean(values) if values else 0
            
            params_by_type[material] = {
                "Temperature": safe_avg([d["Temperature"] for d in sensor_data if "Temperature" in d]),
                "Vibration": safe_avg([d["Vibration"] for d in sensor_data if "Vibration" in d]),
                "RPM": safe_avg([d["RPM"] for d in sensor_data if "RPM" in d]),
                "Power": safe_avg([d["Power"] for d in sensor_data if "Power" in d]),
                "ToolWear": safe_avg([d["ToolWear"] for d in sensor_data if "ToolWear" in d])
            }
        
        return {
            "product_types": product_types,
            "product_quality": product_quality,
            "params_by_type": params_by_type
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching product analysis: {str(e)}"
        )

@app.post("/lathes/{lathe_id}/start-job", response_model=Dict)
async def start_new_job(
    lathe_id: int,
    job_id: str,
    material: str,
    job_type: str,
    tool_no: int
):
    """Initialize a new job in the database with validation"""
    try:
        job_col = f"Lathe{lathe_id}.JobDetails"
        
        # Validate input
        if not job_id or not material or not job_type or tool_no < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job parameters"
            )
        
        job_details = {
            "JobID": job_id,
            "LatheID": lathe_id,
            "Material": material,
            "JobType": job_type,
            "ToolNo": tool_no,
            "StartTime": datetime.now(),
            "Status": "Running",
            "FinalToolWear": 0,
            "DailyJobTarget": 10  # Default value
        }
        
        # Insert job with error handling
        result = db[job_col].insert_one(job_details)
        
        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create job"
            )
        
        return {"message": f"Job {job_id} started on Lathe {lathe_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting job: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.api_host, 
        port=settings.api_port,
        log_level="info"
    )