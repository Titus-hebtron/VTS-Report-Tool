@echo off
echo Starting VTS Backend...
call .venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000