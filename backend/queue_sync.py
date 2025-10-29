from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List

router = APIRouter()

class QueuedEvent(BaseModel):
    endpoint: str
    payload: dict

@router.post("/api/sync/events")
def sync_events(events: List[QueuedEvent]):
    # Example: iterate and process events (or store for async processing)
    processed = []
    for e in events:
        # validate endpoint and payload, e.g. only allow specific endpoints like /patrols/checkin or /incidents
        # For demo, just echo back
        processed.append({"endpoint": e.endpoint, "status": "received"})
    return {"ok": True, "processed": processed}
