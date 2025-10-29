from fastapi import APIRouter, HTTPException, Depends, Request
import os
import boto3
from datetime import timedelta
from pydantic import BaseModel

router = APIRouter()

class PresignRequest(BaseModel):
    filename: str
    content_type: str = "image/jpeg"

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )

@router.post("/api/s3/presign")
def create_presign(req: PresignRequest):
    bucket = os.getenv("S3_BUCKET")
    prefix = os.getenv("S3_PREFIX", "")
    if not bucket:
        raise HTTPException(500, "S3_BUCKET not configured")

    key = f"{prefix}{req.filename}"
    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={'Bucket': bucket, 'Key': key, 'ContentType': req.content_type},
            ExpiresIn=3600
        )
        return {"url": url, "key": key}
    except Exception as e:
        raise HTTPException(500, f"presign failed: {e}")
