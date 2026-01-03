import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sys
sys.path.append('..')
from db_utils import get_sqlalchemy_engine

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(contractor: str, username: str, password: str):
    engine = get_sqlalchemy_engine()
    with engine.begin() as conn:
        # Get contractor_id
        result = conn.execute(
            "SELECT id FROM contractors WHERE name = %s" if not os.getenv("DATABASE_URL", "").startswith("sqlite") else "SELECT id FROM contractors WHERE name = ?",
            (contractor,)
        )
        contractor_row = result.fetchone()
        if not contractor_row:
            return None
        
        contractor_id = contractor_row[0]
        
        # Get user
        result = conn.execute(
            "SELECT id, username, password_hash, role, contractor_id FROM users WHERE contractor_id = %s AND username = %s" if not os.getenv("DATABASE_URL", "").startswith("sqlite") else "SELECT id, username, password_hash, role, contractor_id FROM users WHERE contractor_id = ? AND username = ?",
            (contractor_id, username)
        )
        user = result.fetchone()
        
        if not user:
            return None
        
        if not verify_password(password, user[2]):
            return None
        
        return {
            "id": user[0],
            "username": user[1],
            "role": user[3],
            "contractor": contractor,
            "contractor_id": user[4]
        }

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception