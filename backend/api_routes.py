from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os
sys.path.append('..')
from db_utils import get_sqlalchemy_engine, USE_SQLITE
from backend.auth import authenticate_user, create_access_token, get_current_user

router = APIRouter()

# Auth Models
class LoginRequest(BaseModel):
    contractor: str
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

# Incident Models
class IncidentReportCreate(BaseModel):
    incident_type: str
    patrol_car: str
    incident_date: str
    incident_time: str
    caller: Optional[str] = None
    phone_number: Optional[str] = None
    location: str
    bound: Optional[str] = None
    chainage: Optional[str] = None
    description: Optional[str] = None

# Auth Endpoints
@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = authenticate_user(request.contractor, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"], "contractor_id": user["contractor_id"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# Incident Endpoints
@router.post("/incidents")
async def create_incident(
    incident: IncidentReportCreate,
    current_user: dict = Depends(get_current_user)
):
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        if USE_SQLITE:
            query = """
                INSERT INTO incident_reports 
                (incident_type, patrol_car, incident_date, incident_time, caller, phone_number, 
                 location, bound, chainage, description, uploaded_by, contractor_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        else:
            query = """
                INSERT INTO incident_reports 
                (incident_type, patrol_car, incident_date, incident_time, caller, phone_number, 
                 location, bound, chainage, description, uploaded_by, contractor_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
        
        result = conn.execute(
            query,
            (
                incident.incident_type,
                incident.patrol_car,
                incident.incident_date,
                incident.incident_time,
                incident.caller,
                incident.phone_number,
                incident.location,
                incident.bound,
                incident.chainage,
                incident.description,
                current_user["sub"],
                current_user["contractor_id"],
                datetime.now()
            )
        )
        if USE_SQLITE:
            incident_id = result.lastrowid
        else:
            incident_id = result.fetchone()[0]
        
    return {"id": incident_id, "message": "Incident report created successfully"}

@router.get("/incidents")
async def get_incidents(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        param_marker = "?" if USE_SQLITE else "%s"
        query = f"""
            SELECT id, incident_type, patrol_car, incident_date, incident_time, 
                   location, description, created_at
            FROM incident_reports
            WHERE contractor_id = {param_marker}
            ORDER BY created_at DESC
            LIMIT {param_marker}
        """
        result = conn.execute(query, (current_user["contractor_id"], limit))
        incidents = []
        for row in result:
            incidents.append({
                "id": row[0],
                "incident_type": row[1],
                "patrol_car": row[2],
                "incident_date": str(row[3]),
                "incident_time": str(row[4]),
                "location": row[5],
                "description": row[6],
                "created_at": str(row[7])
            })
    
    return incidents

# Dashboard Stats
@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        param_marker = "?" if USE_SQLITE else "%s"
        
        # Get incident count
        result = conn.execute(
            f"SELECT COUNT(*) FROM incident_reports WHERE contractor_id = {param_marker}",
            (current_user["contractor_id"],)
        )
        incident_count = result.fetchone()[0]
        
        # Get idle reports count
        result = conn.execute(
            f"SELECT COUNT(*) FROM idle_reports WHERE contractor_id = {param_marker}",
            (current_user["contractor_id"],)
        )
        idle_count = result.fetchone()[0]
        
        # Get breaks count
        result = conn.execute(
            f"SELECT COUNT(*) FROM breaks WHERE contractor_id = {param_marker}",
            (current_user["contractor_id"],)
        )
        breaks_count = result.fetchone()[0]
        
        # Get active vehicles count
        result = conn.execute(
            f"SELECT COUNT(DISTINCT vehicle) FROM patrol_logs WHERE vehicle_id IN (SELECT id FROM vehicles WHERE contractor = {param_marker})",
            (current_user.get("contractor", ""),)
        )
        vehicles_count = result.fetchone()[0] or 8
    
    return {
        "incidents": incident_count,
        "idle_reports": idle_count,
        "breaks": breaks_count,
        "vehicles": vehicles_count
    }