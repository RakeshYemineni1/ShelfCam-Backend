# app/services/alert_service.py - COMPLETELY REWRITTEN
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.models.alert import Alert, AlertType, AlertStatus, AlertPriority
from app.models.inventory import Inventory
from app.models.shelf import Shelf
from app.models.staff_assignment import StaffAssignment
from app.models.employee import Employee
from app.models.alert_history import AlertHistory
from app.services.notification_service import NotificationService
from app.services.websocket_service import WebSocketService
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService()
        self.websocket_service = WebSocketService()
        
        # FIXED THRESHOLDS - these make more sense
        self.STOCK_THRESHOLDS = {
            "critical": 0,      # 0% filled = OUT OF STOCK
            "high": 10,         # 0-10% filled = HIGH ALERT
            "medium": 25,       # 10-25% filled = MEDIUM ALERT
            "low": 50           # 25-50% filled = LOW ALERT
        }
    
    def process_json_data(self, json_data: Dict) -> Dict:
        """Main method to process JSON data and create alerts"""
        try:
            logger.info(f"Processing alert data: {json_data}")
            
            alerts_created = []
            errors = []
            
            # Validate JSON structure
            if "shelves" not in json_data:
                raise ValueError("Invalid JSON structure: 'shelves' key missing")
            
            for shelf_data in json_data["shelves"]:
                try:
                    shelf_alerts = self._process_shelf_data(shelf_data)
                    alerts_created.extend(shelf_alerts)
                except Exception as e:
                    error_msg = f"Error processing shelf {shelf_data.get('shelf_id', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            # Send notifications for all created alerts
            for alert in alerts_created:
                self._send_alert_notifications(alert)
            
            logger.info(f"Successfully processed {len(alerts_created)} alerts")
            
            return {
                "success": True,
                "alerts_created": len(alerts_created),
                "alerts": [alert.to_dict() for alert in alerts_created],
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error processing alert data: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "alerts_created": 0,
                "alerts": [],
                "errors": [str(e)]
            }
    
    def _process_shelf_data(self, shelf_data: Dict) -> List[Alert]:
        """Process individual shelf data"""
        alerts = []
        
        shelf_id = shelf_data.get("shelf_id")
        if not shelf_id:
            raise ValueError("shelf_id is required")
        
        logger.info(f"Processing shelf: {shelf_id}")
        
        # Process each rack in the shelf
        for rack_data in shelf_data.get("racks", []):
            try:
                rack_alerts = self._process_rack_data(shelf_id, rack_data)
                alerts.extend(rack_alerts)
            except Exception as e:
                logger.error(f"Error processing rack in shelf {shelf_id}: {str(e)}")
                continue
        
        return alerts
    
    def _process_rack_data(self, shelf_id: str, rack_data: Dict) -> List[Alert]:
        """Process individual rack data and create alerts"""
        alerts = []
        
        # Extract data from JSON
        rack_id = rack_data.get("rack_id")
        detected_item = rack_data.get("item", "")
        empty_percentage = rack_data.get("class_coverage", {}).get("empty", 0.0)
        disordered_percentage = rack_data.get("class_coverage", {}).get("disordered", 0.0)
        
        if not rack_id:
            logger.warning(f"Missing rack_id in shelf {shelf_id}")
            return alerts
        
        # Calculate fill percentage
        fill_percentage = 100.0 - empty_percentage
        
        logger.info(f"Processing rack {rack_id} in shelf {shelf_id}: {fill_percentage:.1f}% filled, item: {detected_item}")
        
        # Find inventory item for this location
        inventory_item = self.db.query(Inventory).filter(
            and_(
                Inventory.shelf_name == shelf_id,
                Inventory.rack_name == rack_id
            )
        ).first()
        
        if not inventory_item:
            logger.warning(f"No inventory item found for {shelf_id}-{rack_id}")
            # Create alert for unknown location
            alert = self._create_unknown_location_alert(shelf_id, rack_id, detected_item)
            if alert:
                alerts.append(alert)
            return alerts
        
        # Check stock levels
        stock_alert = self._check_stock_levels(
            shelf_id, rack_id, inventory_item, fill_percentage, empty_percentage
        )
        if stock_alert:
            alerts.append(stock_alert)
        
        # Check for misplaced items
        misplacement_alert = self._check_misplacement(
            shelf_id, rack_id, detected_item, inventory_item, disordered_percentage
        )
        if misplacement_alert:
            alerts.append(misplacement_alert)
        
        return alerts
    
    def _check_stock_levels(self, shelf_name: str, rack_name: str, 
                           inventory_item: Inventory, fill_percentage: float,
                           empty_percentage: float) -> Optional[Alert]:
        """Check stock levels and create alerts"""
        
        # Determine priority and alert type based on fill percentage
        alert_type = None
        priority = None
        
        if fill_percentage <= self.STOCK_THRESHOLDS["critical"]:
            alert_type = AlertType.OUT_OF_STOCK
            priority = AlertPriority.CRITICAL
        elif fill_percentage <= self.STOCK_THRESHOLDS["high"]:
            alert_type = AlertType.CRITICAL_STOCK
            priority = AlertPriority.HIGH
        elif fill_percentage <= self.STOCK_THRESHOLDS["medium"]:
            alert_type = AlertType.MEDIUM_STOCK
            priority = AlertPriority.MEDIUM
        elif fill_percentage <= self.STOCK_THRESHOLDS["low"]:
            alert_type = AlertType.LOW_STOCK
            priority = AlertPriority.LOW
        
        if not alert_type:
            return None  # Stock level is fine
        
        # Create alert title and message
        priority_emoji = {
            AlertPriority.CRITICAL: "🚨",
            AlertPriority.HIGH: "🔴",
            AlertPriority.MEDIUM: "🟡",
            AlertPriority.LOW: "🟢"
        }
        
        emoji = priority_emoji.get(priority, "📢")
        title = f"{emoji} {priority.value.upper()}: {inventory_item.product_name}"
        
        if fill_percentage <= 0:
            message = f"URGENT: {inventory_item.product_name} is OUT OF STOCK at {shelf_name}-{rack_name}. Immediate restocking required!"
        else:
            message = f"{inventory_item.product_name} is {priority.value} priority at {shelf_name}-{rack_name}. Current stock: {fill_percentage:.1f}% filled."
        
        # Check for existing active alert (avoid duplicates)
        existing_alert = self.db.query(Alert).filter(
            and_(
                Alert.shelf_name == shelf_name,
                Alert.rack_name == rack_name,
                Alert.product_number == inventory_item.product_number,
                Alert.status == AlertStatus.ACTIVE,
                Alert.alert_type.in_([AlertType.LOW_STOCK, AlertType.MEDIUM_STOCK, 
                                    AlertType.HIGH_STOCK, AlertType.CRITICAL_STOCK, 
                                    AlertType.OUT_OF_STOCK])
            )
        ).first()
        
        if existing_alert:
            # Update existing alert
            existing_alert.alert_type = alert_type
            existing_alert.priority = priority
            existing_alert.title = title
            existing_alert.message = message
            existing_alert.empty_percentage = empty_percentage
            existing_alert.fill_percentage = fill_percentage
            existing_alert.updated_at = datetime.utcnow()
            
            # Log the update
            self._log_alert_action(existing_alert.id, "updated", None, f"Stock level updated to {fill_percentage:.1f}%")
            
            return existing_alert
        else:
            # Create new alert
            assigned_staff_id = self._get_assigned_staff_id(shelf_name)
            
            alert = Alert(
                alert_type=alert_type,
                priority=priority,
                status=AlertStatus.ACTIVE,
                shelf_name=shelf_name,
                rack_name=rack_name,
                product_number=inventory_item.product_number,
                product_name=inventory_item.product_name,
                category=inventory_item.category,
                title=title,
                message=message,
                empty_percentage=empty_percentage,
                fill_percentage=fill_percentage,
                assigned_staff_id=assigned_staff_id,
                created_by="system"
            )
            
            self.db.add(alert)
            self.db.flush()  # Get the ID
            
            # Log the creation
            self._log_alert_action(alert.id, "created", None, f"Stock alert created for {fill_percentage:.1f}% fill level")
            
            return alert
    
    def _check_misplacement(self, shelf_name: str, rack_name: str, 
                           detected_item: str, inventory_item: Inventory,
                           disordered_percentage: float) -> Optional[Alert]:
        """Check for misplaced items"""
        
        if not detected_item:
            return None
        
        # Simple item matching (you can enhance this logic)
        expected_item = inventory_item.product_name.lower()
        detected_item_lower = detected_item.lower()
        
        # Check if detected item matches expected item
        is_misplaced = (
            detected_item_lower not in expected_item and 
            expected_item not in detected_item_lower and
            detected_item_lower != expected_item
        )
        
        # Also consider high disorder as misplacement
        if disordered_percentage > 20:  # Threshold for disorder
            is_misplaced = True
        
        if not is_misplaced:
            return None
        
        # Find correct location for the detected item
        correct_location = self._find_correct_location(detected_item)
        
        title = f"🔄 MISPLACED: {detected_item} at {shelf_name}-{rack_name}"
        message = f"Wrong item '{detected_item}' found at {shelf_name}-{rack_name}. Expected: '{inventory_item.product_name}'"
        
        if correct_location:
            message += f" | Correct location: {correct_location}"
        
        if disordered_percentage > 0:
            message += f" | Disorder level: {disordered_percentage:.1f}%"
        
        # Check for existing misplacement alert
        existing_alert = self.db.query(Alert).filter(
            and_(
                Alert.shelf_name == shelf_name,
                Alert.rack_name == rack_name,
                Alert.alert_type == AlertType.MISPLACED_ITEM,
                Alert.status == AlertStatus.ACTIVE
            )
        ).first()
        
        if existing_alert:
            # Update existing alert
            existing_alert.title = title
            existing_alert.message = message
            existing_alert.actual_product = detected_item
            existing_alert.expected_product = inventory_item.product_name
            existing_alert.correct_location = correct_location
            existing_alert.updated_at = datetime.utcnow()
            
            self._log_alert_action(existing_alert.id, "updated", None, f"Misplacement updated: {detected_item}")
            
            return existing_alert
        else:
            # Create new alert
            assigned_staff_id = self._get_assigned_staff_id(shelf_name)
            
            alert = Alert(
                alert_type=AlertType.MISPLACED_ITEM,
                priority=AlertPriority.MEDIUM,
                status=AlertStatus.ACTIVE,
                shelf_name=shelf_name,
                rack_name=rack_name,
                product_number=inventory_item.product_number,
                product_name=inventory_item.product_name,
                category=inventory_item.category,
                title=title,
                message=message,
                expected_product=inventory_item.product_name,
                actual_product=detected_item,
                correct_location=correct_location,
                assigned_staff_id=assigned_staff_id,
                created_by="system"
            )
            
            self.db.add(alert)
            self.db.flush()
            
            self._log_alert_action(alert.id, "created", None, f"Misplacement alert created: {detected_item}")
            
            return alert
    
    def _create_unknown_location_alert(self, shelf_name: str, rack_name: str, 
                                     detected_item: str) -> Optional[Alert]:
        """Create alert for unknown location"""
        
        title = f"❓ UNKNOWN LOCATION: {shelf_name}-{rack_name}"
        message = f"Location {shelf_name}-{rack_name} not found in inventory system. Detected item: '{detected_item}'"
        
        alert = Alert(
            alert_type=AlertType.MISPLACED_ITEM,
            priority=AlertPriority.LOW,
            status=AlertStatus.PENDING,
            shelf_name=shelf_name,
            rack_name=rack_name,
            product_number=None,
            product_name=None,
            category=None,
            title=title,
            message=message,
            actual_product=detected_item,
            assigned_staff_id=None,
            created_by="system"
        )
        
        self.db.add(alert)
        self.db.flush()
        
        self._log_alert_action(alert.id, "created", None, f"Unknown location alert: {shelf_name}-{rack_name}")
        
        return alert
    
    def _find_correct_location(self, item_name: str) -> Optional[str]:
        """Find correct location for misplaced item"""
        
        # Search for item in inventory
        inventory_items = self.db.query(Inventory).filter(
            Inventory.product_name.ilike(f"%{item_name}%")
        ).all()
        
        if inventory_items:
            item = inventory_items[0]  # Take first match
            return f"{item.shelf_name}-{item.rack_name}"
        
        return None
    
    def _get_assigned_staff_id(self, shelf_name: str) -> Optional[str]:
        """Get assigned staff ID for a shelf"""
        
        assignment = self.db.query(StaffAssignment).filter(
            and_(
                StaffAssignment.shelf_id == shelf_name,
                StaffAssignment.is_active == True
            )
        ).first()
        
        return assignment.employee_id if assignment else None
    
    def _send_alert_notifications(self, alert: Alert):
        """Send notifications for alert"""
        
        try:
            # Send to assigned staff
            if alert.assigned_staff_id:
                staff = self.db.query(Employee).filter(
                    Employee.employee_id == alert.assigned_staff_id
                ).first()
                
                if staff and staff.is_active:
                    self.notification_service.send_staff_notification(staff, alert)
                    # Note: WebSocket will be handled by the route
            
            # Send to managers
            managers = self.db.query(Employee).filter(
                and_(
                    Employee.role.in_(["manager", "store_manager"]),
                    Employee.is_active == True
                )
            ).all()
            
            for manager in managers:
                self.notification_service.send_manager_notification(manager, alert)
            
            logger.info(f"Notifications sent for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"Error sending notifications for alert {alert.id}: {str(e)}")
    
    def _log_alert_action(self, alert_id: int, action: str, employee_id: Optional[str], notes: Optional[str]):
        """Log alert action to history"""
        
        try:
            history = AlertHistory(
                alert_id=alert_id,
                action=action,
                performed_by=employee_id,
                notes=notes,
                timestamp=datetime.utcnow()
            )
            self.db.add(history)
        except Exception as e:
            logger.error(f"Error logging alert action: {str(e)}")
    
    # Additional methods for API endpoints
    def get_active_alerts(self, employee_id: Optional[str] = None) -> List[Alert]:
        """Get active alerts"""
        
        query = self.db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE)
        
        if employee_id:
            employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
            if employee and employee.role not in ["manager", "store_manager"]:
                query = query.filter(Alert.assigned_staff_id == employee_id)
        
        return query.order_by(desc(Alert.priority), desc(Alert.created_at)).all()
    
    def acknowledge_alert(self, alert_id: int, employee_id: str) -> bool:
        """Acknowledge an alert"""
        
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            self._log_alert_action(alert_id, "acknowledged", employee_id, "Alert acknowledged")
            
            self.db.commit()
            return True
        
        return False
    
    def resolve_alert(self, alert_id: int, employee_id: str) -> bool:
        """Resolve an alert"""
        
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            self._log_alert_action(alert_id, "resolved", employee_id, "Alert resolved")
            
            self.db.commit()
            return True
        
        return False
    
    def get_alert_statistics(self) -> Dict:
        """Get alert statistics"""
        
        total_active = self.db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).count()
        
        critical_alerts = self.db.query(Alert).filter(
            and_(
                Alert.status == AlertStatus.ACTIVE,
                Alert.priority == AlertPriority.CRITICAL
            )
        ).count()
        
        high_alerts = self.db.query(Alert).filter(
            and_(
                Alert.status == AlertStatus.ACTIVE,
                Alert.priority == AlertPriority.HIGH
            )
        ).count()
        
        stock_alerts = self.db.query(Alert).filter(
            and_(
                Alert.status == AlertStatus.ACTIVE,
                Alert.alert_type.in_([AlertType.LOW_STOCK, AlertType.MEDIUM_STOCK, 
                                    AlertType.HIGH_STOCK, AlertType.CRITICAL_STOCK,
                                    AlertType.OUT_OF_STOCK])
            )
        ).count()
        
        misplaced_alerts = self.db.query(Alert).filter(
            and_(
                Alert.status == AlertStatus.ACTIVE,
                Alert.alert_type == AlertType.MISPLACED_ITEM
            )
        ).count()
        
        return {
            "total_active": total_active,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "stock_alerts": stock_alerts,
            "misplaced_alerts": misplaced_alerts
        }