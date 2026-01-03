import os
import json
import uuid
import datetime
from typing import List
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# dynamic import of python-dotenv to avoid static editor/lint errors when not installed
try:
    import importlib
    _dotenv = importlib.import_module("dotenv")
    _load_dotenv = getattr(_dotenv, "load_dotenv", None)
    if callable(_load_dotenv):
        _load_dotenv()
except Exception:
    # dotenv not available; environment variables should be provided by the runtime environment.
    pass

API_TOKEN = os.getenv("API_TOKEN", "replace_with_device_token")
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
EVENT_STORE_FILE = os.getenv("EVENT_STORE_FILE", "events_store.json")

app = FastAPI(title="VTS Backend - Presign & Batch Ingest")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
try:
    from backend.api_routes import router as api_router
    app.include_router(api_router, prefix="/api")
except ImportError:
    print("Warning: Could not import API routes. Auth endpoints may not be available.")

def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    token = authorization.split(" ", 1)[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

# Replace static boto3 import with dynamic import to avoid editor diagnostics when package not installed
try:
    import importlib
    boto3 = importlib.import_module("boto3")
    ClientError = importlib.import_module("botocore.exceptions").ClientError
except Exception:
    boto3 = None
    ClientError = Exception  # fallback placeholder

# Models
class EventItem(BaseModel):
    patrol_id: str | None = None
    event: str
    timestamp: str | None = None
    location: dict | None = None
    meta: dict | None = None

class BatchPayload(BaseModel):
    device_id: str | None = None
    events: List[EventItem]

# S3 presign helper (PUT)
def get_presigned_put_url(object_name: str, expiration=3600):
    # If boto3 is not installed/configured, raise an informative error instead of failing with ImportError
    if boto3 is None:
        raise RuntimeError(
            "boto3 is not available in this environment. Install it with 'pip install boto3' "
            "and ensure AWS credentials are configured to enable S3 presigned uploads."
        )
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET not configured")
    session = boto3.session.Session()
    s3_client = session.client('s3', region_name=AWS_REGION)
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={'Bucket': S3_BUCKET, 'Key': object_name, 'ACL': 'private'},
            ExpiresIn=expiration
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}")
    return url

@app.post("/api/presign")
def presign_upload(filename: str, token: str = Depends(verify_token)):
    """
    Returns a presigned PUT URL for direct client upload to S3.
    Client should PUT binary bytes to returned url with Content-Type set.
    """
    key = f"uploads/{uuid.uuid4().hex}_{os.path.basename(filename)}"
    url = get_presigned_put_url(key)
    return {"ok": True, "upload_url": url, "key": key}

@app.post("/api/events/batch")
def ingest_batch(payload: BatchPayload, token: str = Depends(verify_token)):
    """
    Accepts a batch of events (queued from mobile when offline).
    Stores to a local JSON file (append). Adjust to use DB in production.
    """
    out = []
    timestamp = datetime.datetime.utcnow().isoformat()
    store = []
    # read existing
    if os.path.exists(EVENT_STORE_FILE):
        try:
            with open(EVENT_STORE_FILE, "r", encoding="utf-8") as f:
                store = json.load(f)
        except Exception:
            store = []
    for ev in payload.events:
        entry = {
            "id": uuid.uuid4().hex,
            "device_id": payload.device_id,
            "event": ev.event,
            "patrol_id": ev.patrol_id,
            "timestamp": ev.timestamp or datetime.datetime.utcnow().isoformat(),
            "location": ev.location,
            "meta": ev.meta,
            "ingested_at": timestamp
        }
        store.append(entry)
        out.append({"ok": True, "id": entry["id"]})
    # write back
    with open(EVENT_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, default=str)
    return {"ok": True, "ingested": len(out), "results": out}

@app.get("/api/events")
def list_events(token: str = Depends(verify_token)):
    if os.path.exists(EVENT_STORE_FILE):
        with open(EVENT_STORE_FILE, "r", encoding="utf-8") as f:
            try:
                return {"events": json.load(f)}
            except Exception:
                return {"events": []}
    return {"events": []}

# --- Convenience runner: start backend + Streamlit UI together ----------------
if __name__ == "__main__":
    import threading
    import subprocess
    import sys
    import time
    print("Starting VTS backend + Streamlit UI (convenience runner).")

    # Start uvicorn in a thread (if uvicorn installed)
    try:
        import importlib
        uvicorn = importlib.import_module("uvicorn")
    except Exception:
        uvicorn = None

    def _run_uvicorn():
        if uvicorn is None:
            print("uvicorn not available. Install with: pip install uvicorn[standard]")
            return
        # run the current module's FastAPI app
        try:
            uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, log_level="info")
        except Exception as e:
            print("Failed to start uvicorn:", e)

    uv_thread = threading.Thread(target=_run_uvicorn, daemon=True)
    uv_thread.start()

    # wait a little for backend to initialize
    time.sleep(1.5)

    # Launch Streamlit UI pointing to the top-level incident_report.py
    streamlit_cmd = None
    try:
        import importlib
        _ = importlib.import_module("streamlit")
        streamlit_cmd = ["streamlit", "run", os.path.join(os.path.dirname(os.path.dirname(__file__)), "incident_report.py")]
    except Exception:
        # streamlit not importable; still attempt to run CLI if available in PATH
        streamlit_cmd = ["streamlit", "run", os.path.join(os.path.dirname(os.path.dirname(__file__)), "incident_report.py")]

    print("Launching Streamlit UI:", " ".join(streamlit_cmd))
    try:
        # This call will block until Streamlit process exits; it's intended for local convenience.
        subprocess.run(streamlit_cmd, check=False)
    except FileNotFoundError:
        print("Streamlit CLI not found. Install with: pip install streamlit")
        print("Or run Streamlit manually:")
        print(f"  streamlit run {os.path.join(os.path.dirname(os.path.dirname(__file__)), 'incident_report.py')}")
    except Exception as e:
        print("Failed to launch Streamlit:", e)

    # Keep main thread alive while uvicorn thread runs (if any)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down runner.")
        sys.exit(0)