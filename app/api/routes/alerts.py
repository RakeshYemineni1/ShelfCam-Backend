# app/api/routes/alerts.py - Complete alerts routes
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import json
import logging

from app.database.db import get_db
from app.services.alert_service import AlertService
from app.models.employee import Employee
from app.models.alert import Alert, AlertType, AlertStatus, AlertPriority
from app.models.alert_history import AlertHistory

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process")
async def process_alerts(
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
        
        # Validate JSON structure for new format
        required_fields = ["shelf_number", "empty_percentage", "items_detected"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Validate data types
        if not isinstance(data["shelf_number"], str):
            raise HTTPException(status_code=400, detail="shelf_number must be a string")
        
        if not isinstance(data["empty_percentage"], (int, float)):
            raise HTTPException(status_code=400, detail="empty_percentage must be a number")
        
        if not isinstance(data["items_detected"], list):
            raise HTTPException(status_code=400, detail="items_detected must be an array")
        
        # Process alerts using AlertService
        alert_service = AlertService(db)
        result = alert_service.process_json_data(data)
        
        if not result["success"]:
            logger.error(f"Alert processing failed: {result['error']}")
            raise HTTPException(status_code=500, detail=f"Alert processing failed: {result['error']}")
        
        # Return success response
        response = {
            "message": "Alerts processed successfully",
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

@router.get("/active")
async def get_active_alerts(
    employee_id: Optional[str] = Query(None, description="Filter alerts by employee ID"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    shelf_name: Optional[str] = Query(None, description="Filter by shelf name"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of alerts to return"),
    db: Session = Depends(get_db)
):
    """Get active alerts for dashboard display with optional filtering"""
    
    try:
        alert_service = AlertService(db)
        
        # Get base active alerts
        alerts = alert_service.get_active_alerts(employee_id)
        
        # Apply additional filters
        if priority:
            try:
                priority_enum = AlertPriority(priority.upper())
                alerts = [alert for alert in alerts if alert.priority == priority_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
        
        if alert_type:
            try:
                type_enum = AlertType(alert_type.upper())
                alerts = [alert for alert in alerts if alert.alert_type == type_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        if shelf_name:
            alerts = [alert for alert in alerts if alert.shelf_name == shelf_name]
        
        # Apply limit
        alerts = alerts[:limit]
        
        return {
            "success": True,
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts),
            "total_active": len(alert_service.get_active_alerts())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching active alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")

@router.get("/dashboard/{employee_id}")
async def get_dashboard_alerts(
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Get alerts for specific employee dashboard"""
    
    try:
        # Validate employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        alert_service = AlertService(db)
        alerts = alert_service.get_active_alerts(employee_id)
        statistics = alert_service.get_alert_statistics()
        
        return {
            "success": True,
            "employee": {
                "employee_id": employee.employee_id,
                "username": employee.username,
                "role": employee.role
            },
            "alerts": [alert.to_dict() for alert in alerts],
            "statistics": statistics,
            "count": len(alerts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard alerts for {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard alerts: {str(e)}")

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

@router.get("/history/{alert_id}")
async def get_alert_history(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get history for a specific alert"""
    
    try:
        # Validate alert exists
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Get alert history
        history = db.query(AlertHistory).filter(
            AlertHistory.alert_id == alert_id
        ).order_by(AlertHistory.timestamp.desc()).all()
        
        history_data = []
        for record in history:
            history_data.append({
                "id": record.id,
                "action": record.action,
                "performed_by": record.performed_by,
                "notes": record.notes,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None
            })
        
        return {
            "success": True,
            "alert": alert.to_dict(),
            "history": history_data,
            "count": len(history_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert history for {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching alert history: {str(e)}")

@router.get("/statistics")
async def get_alert_statistics(
    db: Session = Depends(get_db)
):
    """Get comprehensive alert statistics"""
    
    try:
        alert_service = AlertService(db)
        statistics = alert_service.get_alert_statistics()
        
        # Add additional statistics
        total_alerts = db.query(Alert).count()
        resolved_alerts = db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()
        acknowledged_alerts = db.query(Alert).filter(Alert.status == AlertStatus.ACKNOWLEDGED).count()
        
        statistics.update({
            "total_alerts": total_alerts,
            "resolved_alerts": resolved_alerts,
            "acknowledged_alerts": acknowledged_alerts
        })
        
        return {
            "success": True,
            "statistics": statistics
        }
        
    except Exception as e:
        logger.error(f"Error fetching alert statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

@router.get("/")
async def get_all_alerts(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ACKNOWLEDGED, RESOLVED, PENDING)"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    shelf_name: Optional[str] = Query(None, description="Filter by shelf name"),
    employee_id: Optional[str] = Query(None, description="Filter by assigned employee"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    db: Session = Depends(get_db)
):
    """Get all alerts with filtering and pagination"""
    
    try:
        # Build query
        query = db.query(Alert)
        
        # Apply filters
        if status:
            try:
                status_enum = AlertStatus(status.upper())
                query = query.filter(Alert.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        if priority:
            try:
                priority_enum = AlertPriority(priority.upper())
                query = query.filter(Alert.priority == priority_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
        
        if alert_type:
            try:
                type_enum = AlertType(alert_type.upper())
                query = query.filter(Alert.alert_type == type_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        if shelf_name:
            query = query.filter(Alert.shelf_name == shelf_name)
        
        if employee_id:
            query = query.filter(Alert.assigned_staff_id == employee_id)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "success": True,
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts),
            "total_count": total_count,
            "offset": offset,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")

@router.get("/{alert_id}")
async def get_alert_details(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific alert"""
    
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Get assigned employee info if available
        assigned_employee = None
        if alert.assigned_staff_id:
            employee = db.query(Employee).filter(Employee.employee_id == alert.assigned_staff_id).first()
            if employee:
                assigned_employee = {
                    "employee_id": employee.employee_id,
                    "username": employee.username,
                    "role": employee.role
                }
        
        # Get recent history (last 5 actions)
        recent_history = db.query(AlertHistory).filter(
            AlertHistory.alert_id == alert_id
        ).order_by(AlertHistory.timestamp.desc()).limit(5).all()
        
        history_data = []
        for record in recent_history:
            history_data.append({
                "action": record.action,
                "performed_by": record.performed_by,
                "notes": record.notes,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None
            })
        
        alert_data = alert.to_dict()
        alert_data["assigned_employee"] = assigned_employee
        alert_data["recent_history"] = history_data
        
        return {
            "success": True,
            "alert": alert_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert details for {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching alert details: {str(e)}")

@router.post("/bulk-acknowledge")
async def bulk_acknowledge_alerts(
    alert_ids: List[int],
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Acknowledge multiple alerts at once"""
    
    try:
        # Validate employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not alert_ids:
            raise HTTPException(status_code=400, detail="No alert IDs provided")
        
        alert_service = AlertService(db)
        successful_count = 0
        failed_alerts = []
        
        for alert_id in alert_ids:
            try:
                success = alert_service.acknowledge_alert(alert_id, employee_id)
                if success:
                    successful_count += 1
                else:
                    failed_alerts.append(alert_id)
            except Exception as e:
                logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
                failed_alerts.append(alert_id)
        
        return {
            "success": True,
            "message": f"Successfully acknowledged {successful_count} alerts",
            "successful_count": successful_count,
            "failed_alerts": failed_alerts,
            "total_requested": len(alert_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk acknowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in bulk acknowledge: {str(e)}")

@router.post("/bulk-resolve")
async def bulk_resolve_alerts(
    alert_ids: List[int],
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Resolve multiple alerts at once"""
    
    try:
        # Validate employee exists
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not alert_ids:
            raise HTTPException(status_code=400, detail="No alert IDs provided")
        
        alert_service = AlertService(db)
        successful_count = 0
        failed_alerts = []
        
        for alert_id in alert_ids:
            try:
                success = alert_service.resolve_alert(alert_id, employee_id)
                if success:
                    successful_count += 1
                else:
                    failed_alerts.append(alert_id)
            except Exception as e:
                logger.error(f"Error resolving alert {alert_id}: {str(e)}")
                failed_alerts.append(alert_id)
        
        return {
            "success": True,
            "message": f"Successfully resolved {successful_count} alerts",
            "successful_count": successful_count,
            "failed_alerts": failed_alerts,
            "total_requested": len(alert_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk resolve: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in bulk resolve: {str(e)}")

@router.get("/shelf/{shelf_name}")
async def get_shelf_alerts(
    shelf_name: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get all alerts for a specific shelf"""
    
    try:
        query = db.query(Alert).filter(Alert.shelf_name == shelf_name)
        
        if status:
            try:
                status_enum = AlertStatus(status.upper())
                query = query.filter(Alert.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        alerts = query.order_by(Alert.created_at.desc()).all()
        
        return {
            "success": True,
            "shelf_name": shelf_name,
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching shelf alerts for {shelf_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching shelf alerts: {str(e)}")