from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt
import bcrypt
from datetime import datetime, timedelta
from db_utils import get_sqlalchemy_engine, get_contractor_id, init_database
from sqlalchemy import text
import pandas as pd

# Initialize database on startup
init_database()

app = FastAPI(title="VTS Report Tool API")

SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

class LoginRequest(BaseModel):
    contractor: str
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        contractor: str = payload.get("contractor")
        role: str = payload.get("role")
        if username is None or contractor is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "contractor": contractor, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    engine = get_sqlalchemy_engine()
    conn = engine.raw_connection()
    cur = conn.cursor()

    cur.execute("SELECT u.id, u.password_hash, u.role FROM users u JOIN contractors c ON u.contractor_id = c.id WHERE c.name = %s AND u.username = %s",
                (request.contractor, request.username))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and bcrypt.checkpw(request.password.encode('utf-8'), user[1].encode('utf-8')):
        role = "re_admin" if request.contractor == "RE Office" else user[2]
        access_token = create_access_token(
            data={"sub": request.username, "contractor": request.contractor, "role": role},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/vehicles")
def get_vehicles(user: dict = Depends(verify_token)):
    contractor = user["contractor"]
    contractor_id = get_contractor_id(contractor)
    engine = get_sqlalchemy_engine()
    query = text("""
        SELECT id, plate_number
        FROM vehicles
        WHERE contractor = :contractor
        ORDER BY plate_number
    """)
    with engine.begin() as conn:
        result = conn.execute(query, {"contractor": contractor})
        vehicles = [{"id": row[0], "plate_number": row[1]} for row in result.fetchall()]
    return vehicles

class PatrolLogRequest(BaseModel):
    vehicle_id: int
    latitude: float
    longitude: float
    timestamp: str
    activity: str
    speed: float
    status: str = "online"

@app.post("/patrol_logs")
def create_patrol_log(log: PatrolLogRequest, user: dict = Depends(verify_token)):
    engine = get_sqlalchemy_engine()
    insert_query = """
        INSERT INTO patrol_logs (vehicle_id, timestamp, latitude, longitude, activity)
        VALUES (:vehicle_id, :timestamp, :latitude, :longitude, :activity)
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(insert_query), {
                "vehicle_id": log.vehicle_id,
                "timestamp": log.timestamp,
                "latitude": log.latitude,
                "longitude": log.longitude,
                "activity": log.activity
            })
        return {"message": "Patrol log created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create patrol log: {str(e)}")

@app.get("/patrol_logs/{vehicle_id}")
def get_patrol_logs(vehicle_id: int, user: dict = Depends(verify_token)):
    engine = get_sqlalchemy_engine()
    logs_query = """
        SELECT timestamp, latitude, longitude, activity
        FROM patrol_logs
        WHERE vehicle_id = :vehicle_id
        ORDER BY timestamp DESC
    """
    with engine.begin() as conn:
        patrol_logs = pd.read_sql(logs_query, conn, params={"vehicle_id": vehicle_id})
    return patrol_logs.to_dict(orient="records")

class IdleReportRequest(BaseModel):
    vehicle: str
    idle_start: str
    location_address: str
    latitude: float
    longitude: float
    description: str
    contractor_id: str

class IdleReportEndRequest(BaseModel):
    vehicle: str
    idle_end: str
    idle_duration_min: float

@app.post("/idle_reports")
def create_idle_report(report: IdleReportRequest, user: dict = Depends(verify_token)):
    engine = get_sqlalchemy_engine()
    insert_query = """
        INSERT INTO idle_reports (vehicle, idle_start, location_address, latitude, longitude, description, contractor_id, uploaded_by)
        VALUES (:vehicle, :idle_start, :location_address, :latitude, :longitude, :description, :contractor_id, :uploaded_by)
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(insert_query), {
                "vehicle": report.vehicle,
                "idle_start": report.idle_start,
                "location_address": report.location_address,
                "latitude": report.latitude,
                "longitude": report.longitude,
                "description": report.description,
                "contractor_id": report.contractor_id,
                "uploaded_by": user["username"]
            })
        return {"message": "Idle report created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create idle report: {str(e)}")

@app.put("/idle_reports/end")
def end_idle_report(report: IdleReportEndRequest, user: dict = Depends(verify_token)):
    engine = get_sqlalchemy_engine()
    update_query = """
        UPDATE idle_reports
        SET idle_end = :idle_end, idle_duration_min = :idle_duration_min
        WHERE vehicle = :vehicle AND idle_end IS NULL
        ORDER BY idle_start DESC LIMIT 1
    """
    try:
        with engine.begin() as conn:
            result = conn.execute(text(update_query), {
                "vehicle": report.vehicle,
                "idle_end": report.idle_end,
                "idle_duration_min": report.idle_duration_min
            })
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="No active idle report found")
        return {"message": "Idle report updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update idle report: {str(e)}")

@app.get("/incidents")
def get_incidents(user: dict = Depends(verify_token)):
    contractor = user["contractor"]
    contractor_id = get_contractor_id(contractor)
    engine = get_sqlalchemy_engine()
    query = "SELECT * FROM incident_reports WHERE contractor_id = %s ORDER BY incident_date DESC LIMIT 50"
    with engine.begin() as conn:
        incidents = pd.read_sql(query, conn, params=(contractor_id,))
    return incidents.to_dict(orient="records")

# Add more endpoints as needed for reports

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)