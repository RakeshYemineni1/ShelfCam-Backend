# app/api/routes/alerts.py - FIXED VERSION
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

from app.database.db import get_db
from app.services.alert_service import AlertService
from app.services.websocket_service import WebSocketService
from app.models.employee import Employee

router = APIRouter()
logger = logging.getLogger(__name__)
socket_manager = WebSocketService()

@router.post("/process")
async def process_alerts(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """Process alerts from uploaded JSON file"""
    
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")
        
        # Read and parse JSON data
        try:
            content = await file.read()
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
        # Validate JSON structure
        if not isinstance(data, dict) or "shelves" not in data:
            raise HTTPException(status_code=400, detail="Invalid JSON structure: 'shelves' key is required")
        
        if not isinstance(data["shelves"], list):
            raise HTTPException(status_code=400, detail="Invalid JSON structure: 'shelves' must be an array")
        
        # Process alerts using AlertService
        alert_service = AlertService(db)
        result = alert_service.process_json_data(data)
        
        if not result["success"]:
            logger.error(f"Alert processing failed: {result['error']}")
            raise HTTPException(status_code=500, detail=f"Alert processing failed: {result['error']}")
        
        # Send WebSocket notifications in background
        if result["alerts"]:
            background_tasks.add_task(send_websocket_notifications, result["alerts"])
        
        # Return success response
        response = {
            "message": "Alerts processed and dispatched successfully",
            "alerts_created": result["alerts_created"],
            "success": True
        }
        
        # Include errors if any (non-critical)
        if result["errors"]:
            response["warnings"] = result["errors"]
            logger.warning(f"Processing completed with warnings: {result['errors']}")
        
        logger.info(f"Successfully processed {result['alerts_created']} alerts")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def send_websocket_notifications(alerts_data: list):
    """Send WebSocket notifications for alerts in background"""
    
    try:
        for alert_data in alerts_data:
            # Send to assigned staff
            if alert_data.get("assigned_staff_id"):
                await socket_manager.send_alert_to_user(
                    alert_data["assigned_staff_id"], 
                    alert_data
                )
            
            # Send to managers (you might want to get manager IDs from DB)
            # This is a simplified approach - you can enhance based on your needs
            await socket_manager.broadcast_alert_to_managers(alert_data)
            
    except Exception as e:
        logger.error(f"Error sending WebSocket notifications: {str(e)}")

@router.get("/active")
async def get_active_alerts(
    employee_id: str = None,
    db: Session = Depends(get_db)
):
    """Get active alerts for an employee or all alerts for managers"""
    
    try:
        alert_service = AlertService(db)
        alerts = alert_service.get_active_alerts(employee_id)
        
        return {
            "success": True,
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error fetching active alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")

@router.post("/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: int,
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Acknowledge an alert"""
    
    try:
        # Validate employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        alert_service = AlertService(db)
        success = alert_service.acknowledge_alert(alert_id, employee_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already processed")
        
        return {
            "success": True,
            "message": "Alert acknowledged successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

@router.post("/resolve/{alert_id}")
async def resolve_alert(
    alert_id: int,
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Resolve an alert"""
    
    try:
        # Validate employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        alert_service = AlertService(db)
        success = alert_service.resolve_alert(alert_id, employee_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or cannot be resolved")
        
        return {
            "success": True,
            "message": "Alert resolved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")

@router.get("/statistics")
async def get_alert_statistics(db: Session = Depends(get_db)):
    """Get alert statistics"""
    
    try:
        alert_service = AlertService(db)
        stats = alert_service.get_alert_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error fetching alert statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

@router.get("/history/{alert_id}")
async def get_alert_history(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get alert history"""
    
    try:
        from app.models.alert_history import AlertHistory
        
        history = db.query(AlertHistory).filter(
            AlertHistory.alert_id == alert_id
        ).order_by(AlertHistory.timestamp.desc()).all()
        
        return {
            "success": True,
            "history": [
                {
                    "id": h.id,
                    "action": h.action,
                    "performed_by": h.performed_by,
                    "notes": h.notes,
                    "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                    "employee": {
                        "employee_id": h.employee.employee_id,
                        "username": h.employee.username
                    } if h.employee else None
                }
                for h in history
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching alert history for {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching alert history: {str(e)}")

# Additional utility endpoint for testing
@router.post("/test-sample")
async def test_sample_data(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Test endpoint using sample data"""
    
    sample_data = {
        "shelves": [
            {
                "shelf_id": "kkkk",
                "file_path": "runs/detect/predict/labels/image1.txt",
                "image_name": "image1",
                "class_coverage": {
                    "empty": 28.18,
                    "disordered": 12.12
                },
                "racks": [
                    {
                        "rack_id": "R4",
                        "class_coverage": {
                            "empty": 70.04,
                            "disordered": 12.55
                        },
                        "item": "m&m"
                    }
                ]
            }
        ]
    }
    
    try:
        alert_service = AlertService(db)
        result = alert_service.process_json_data(sample_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Alert processing failed: {result['error']}")
        
        # Send WebSocket notifications in background
        if result["alerts"]:
            background_tasks.add_task(send_websocket_notifications, result["alerts"])
        
        return {
            "message": "Sample data processed successfully",
            "alerts_created": result["alerts_created"],
            "success": True,
            "sample_data": sample_data
        }
        
    except Exception as e:
        logger.error(f"Error processing sample data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing sample data: {str(e)}")