# app/api/routes/detect.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import json
import logging

from app.database.db import get_db
from app.services.model_runner import run_model_on_image
from app.services.alert_service import AlertService

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("static/uploads")
OUTPUT_JSON = Path("static/outputs/output.json")

@router.post("/detect/")
async def detect_and_alert(
    file: UploadFile = File(...),
    shelf_number: str = "A1",
    db: Session = Depends(get_db)
):
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        upload_path = UPLOAD_DIR / file.filename
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        success = run_model_on_image(str(upload_path), shelf_number)
        if not success:
            raise HTTPException(status_code=500, detail="Model failed")

        if not OUTPUT_JSON.exists():
            raise HTTPException(status_code=500, detail="output.json not found")

        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)

        alert_service = AlertService(db)
        result = alert_service.process_json_data(data)

        return {
            "success": True,
            "alerts_created": result["alerts_created"],
            "alerts": result["alerts"],
            "warnings": result["errors"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
