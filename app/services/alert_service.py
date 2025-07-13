# app/services/alert_service.py - REWRITTEN for shelf-level detection
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
        
        # SHELF-LEVEL STOCK THRESHOLDS
        self.STOCK_THRESHOLDS = {
            "critical": 10,     # < 10% filled (>90% empty) = CRITICAL
            "high": 25,         # < 25% filled (>75% empty) = HIGH
            "medium": 50,       # < 50% filled (>50% empty) = MEDIUM
            "low": 75           # < 75% filled (>25% empty) = LOW
        }
    
    def process_json_data(self, json_data: Dict) -> Dict:
        """Main method to process JSON data and create alerts"""
        try:
            logger.info(f"Processing alert data: {json_data}")
            
            alerts_created = []
            errors = []
            
            # Process single shelf data
            shelf_number = json_data.get("shelf_number")
            empty_percentage = json_data.get("empty_percentage", 0.0)
            items_detected = json_data.get("items_detected", [])
            
            if not shelf_number:
                raise ValueError("Invalid JSON structure: 'shelf_number' is required")
            
            try:
                shelf_alerts = self._process_shelf_data(shelf_number, empty_percentage, items_detected)
                alerts_created.extend(shelf_alerts)
            except Exception as e:
                error_msg = f"Error processing shelf {shelf_number}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            # Send notifications for all created alerts
            for alert in alerts_created:
                self._send_alert_notifications(alert)
            
            logger.info(f"Successfully processed {len(alerts_created)} alerts for shelf {shelf_number}")
            
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
    
    def _process_shelf_data(self, shelf_number: str, empty_percentage: float, items_detected: List[str]) -> List[Alert]:
        """Process shelf data and create alerts"""
        alerts = []
        
        logger.info(f"Processing shelf {shelf_number}: {empty_percentage}% empty, items: {items_detected}")
        
        # Calculate fill percentage
        fill_percentage = 100.0 - empty_percentage
        
        # Check if shelf exists in database
        shelf = self.db.query(Shelf).filter(Shelf.name == shelf_number).first()
        if not shelf:
            logger.warning(f"Shelf {shelf_number} not found in database")
            # Create alert for unknown shelf
            unknown_alert = self._create_unknown_shelf_alert(shelf_number, items_detected)
            if unknown_alert:
                alerts.append(unknown_alert)
            return alerts
        
        # Get inventory items for this shelf
        inventory_items = self.db.query(Inventory).filter(
            Inventory.shelf_name == shelf_number
        ).all()
        
        # Check stock levels
        stock_alert = self._check_stock_levels(shelf_number, fill_percentage, empty_percentage, inventory_items)
        if stock_alert:
            alerts.append(stock_alert)
        
        # Check for misplaced items
        misplacement_alerts = self._check_misplacement(shelf_number, items_detected, inventory_items)
        alerts.extend(misplacement_alerts)
        
        return alerts
    
    def _check_stock_levels(self, shelf_name: str, fill_percentage: float, 
                           empty_percentage: float, inventory_items: List[Inventory]) -> Optional[Alert]:
        """Check stock levels and create alerts"""
        
        # Determine priority and alert type based on fill percentage
        alert_type = None
        priority = None
        
        if fill_percentage < self.STOCK_THRESHOLDS["critical"]:
            alert_type = AlertType.CRITICAL_STOCK if fill_percentage > 0 else AlertType.OUT_OF_STOCK
            priority = AlertPriority.CRITICAL
        elif fill_percentage < self.STOCK_THRESHOLDS["high"]:
            alert_type = AlertType.HIGH_STOCK
            priority = AlertPriority.HIGH
        elif fill_percentage < self.STOCK_THRESHOLDS["medium"]:
            alert_type = AlertType.MEDIUM_STOCK
            priority = AlertPriority.MEDIUM
        elif fill_percentage < self.STOCK_THRESHOLDS["low"]:
            alert_type = AlertType.LOW_STOCK
            priority = AlertPriority.LOW
        
        if not alert_type:
            # Stock level is fine, remove any existing stock alerts
            self._resolve_existing_stock_alerts(shelf_name)
            return None
        
        # Create alert title and message
        priority_emoji = {
            AlertPriority.CRITICAL: "🚨",
            AlertPriority.HIGH: "🔴",
            AlertPriority.MEDIUM: "🟡",
            AlertPriority.LOW: "🟢"
        }
        
        emoji = priority_emoji.get(priority, "📢")
        
        if alert_type == AlertType.OUT_OF_STOCK:
            title = f"{emoji} OUT OF STOCK: Shelf {shelf_name}"
            message = f"URGENT: Shelf {shelf_name} is completely empty (0% filled). Immediate restocking required!"
        else:
            title = f"{emoji} {priority.value.upper()} STOCK: Shelf {shelf_name}"
            message = f"Shelf {shelf_name} has {priority.value} stock levels. Current fill: {fill_percentage:.1f}%"
        
        # Get shelf categories for context
        categories = list(set([item.category for item in inventory_items if item.category]))
        category_text = ", ".join(categories) if categories else "Mixed"
        
        # Check for existing active stock alert
        existing_alert = self.db.query(Alert).filter(
            and_(
                Alert.shelf_name == shelf_name,
                Alert.rack_name.is_(None),  # Shelf-level alert
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
            existing_alert.category = category_text
            existing_alert.updated_at = datetime.utcnow()
            
            # Log the update
            self._log_alert_action(existing_alert.id, "updated", None, 
                                 f"Stock level updated to {fill_percentage:.1f}%")
            
            logger.info(f"Updated existing stock alert for shelf {shelf_name}")
            return existing_alert
        else:
            # Create new alert
            assigned_staff_id = self._get_assigned_staff_id(shelf_name)
            
            alert = Alert(
                alert_type=alert_type,
                priority=priority,
                status=AlertStatus.ACTIVE,
                shelf_name=shelf_name,
                rack_name=None,  # Shelf-level alert
                product_number=None,  # Shelf-level, not product-specific
                product_name=None,
                category=category_text,
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
            self._log_alert_action(alert.id, "created", None, 
                                 f"Stock alert created for {fill_percentage:.1f}% fill level")
            
            logger.info(f"Created new stock alert for shelf {shelf_name}")
            return alert
    
    def _check_misplacement(self, shelf_name: str, items_detected: List[str], 
                           inventory_items: List[Inventory]) -> List[Alert]:
        """Check for misplaced items on shelf"""
        
        alerts = []
        
        if not items_detected:
            return alerts
        
        # Get expected item names for this shelf
        expected_items = set([item.product_name.lower() for item in inventory_items])
        
        # Check each detected item
        for detected_item in items_detected:
            if not detected_item:
                continue
                
            detected_item_lower = detected_item.lower()
            
            # Check if detected item matches any expected item (fuzzy matching)
            is_expected = any(
                detected_item_lower in expected.lower() or 
                expected.lower() in detected_item_lower or
                detected_item_lower == expected.lower()
                for expected in expected_items
            )
            
            if not is_expected:
                # This is a misplaced item
                misplacement_alert = self._create_misplacement_alert(
                    shelf_name, detected_item, inventory_items
                )
                if misplacement_alert:
                    alerts.append(misplacement_alert)
        
        # Also check for missing expected items (if shelf is not empty)
        if items_detected and len(items_detected) > 0:
            missing_items = []
            for inventory_item in inventory_items:
                item_found = any(
                    inventory_item.product_name.lower() in detected.lower() or
                    detected.lower() in inventory_item.product_name.lower()
                    for detected in items_detected
                )
                if not item_found:
                    missing_items.append(inventory_item.product_name)
            
            if missing_items:
                missing_alert = self._create_missing_items_alert(shelf_name, missing_items)
                if missing_alert:
                    alerts.append(missing_alert)
        
        return alerts
    
    def _create_misplacement_alert(self, shelf_name: str, detected_item: str, 
                                  inventory_items: List[Inventory]) -> Optional[Alert]:
        """Create alert for misplaced item"""
        
        # Find correct location for the detected item
        correct_location = self._find_correct_location(detected_item)
        
        title = f"🔄 MISPLACED: {detected_item} on Shelf {shelf_name}"
        message = f"Wrong item '{detected_item}' found on shelf {shelf_name}."
        
        # Add expected items context
        if inventory_items:
            expected_names = [item.product_name for item in inventory_items[:3]]  # First 3 items
            message += f" Expected items: {', '.join(expected_names)}"
            if len(inventory_items) > 3:
                message += f" (and {len(inventory_items) - 3} more)"
        
        if correct_location:
            message += f" | Correct location: {correct_location}"
        
        # Check for existing misplacement alert for this item
        existing_alert = self.db.query(Alert).filter(
            and_(
                Alert.shelf_name == shelf_name,
                Alert.alert_type == AlertType.MISPLACED_ITEM,
                Alert.actual_product == detected_item,
                Alert.status == AlertStatus.ACTIVE
            )
        ).first()
        
        if existing_alert:
            # Update existing alert
            existing_alert.title = title
            existing_alert.message = message
            existing_alert.correct_location = correct_location
            existing_alert.updated_at = datetime.utcnow()
            
            self._log_alert_action(existing_alert.id, "updated", None, 
                                 f"Misplacement updated: {detected_item}")
            
            return existing_alert
        else:
            # Create new alert
            assigned_staff_id = self._get_assigned_staff_id(shelf_name)
            
            alert = Alert(
                alert_type=AlertType.MISPLACED_ITEM,
                priority=AlertPriority.MEDIUM,
                status=AlertStatus.ACTIVE,
                shelf_name=shelf_name,
                rack_name=None,  # Shelf-level
                product_number=None,
                product_name=None,
                category=inventory_items[0].category if inventory_items else None,
                title=title,
                message=message,
                expected_product=inventory_items[0].product_name if inventory_items else None,
                actual_product=detected_item,
                correct_location=correct_location,
                assigned_staff_id=assigned_staff_id,
                created_by="system"
            )
            
            self.db.add(alert)
            self.db.flush()
            
            self._log_alert_action(alert.id, "created", None, 
                                 f"Misplacement alert created: {detected_item}")
            
            return alert
    
    def _create_missing_items_alert(self, shelf_name: str, missing_items: List[str]) -> Optional[Alert]:
        """Create alert for missing expected items"""
        
        if not missing_items:
            return None
        
        title = f"❌ MISSING ITEMS: Shelf {shelf_name}"
        message = f"Expected items not detected on shelf {shelf_name}: {', '.join(missing_items[:5])}"
        
        if len(missing_items) > 5:
            message += f" (and {len(missing_items) - 5} more)"
        
        # Check for existing missing items alert
        existing_alert = self.db.query(Alert).filter(
            and_(
                Alert.shelf_name == shelf_name,
                Alert.alert_type == AlertType.MISPLACED_ITEM,
                Alert.title.like("%MISSING ITEMS%"),
                Alert.status == AlertStatus.ACTIVE
            )
        ).first()
        
        if existing_alert:
            # Update existing alert
            existing_alert.title = title
            existing_alert.message = message
            existing_alert.updated_at = datetime.utcnow()
            
            self._log_alert_action(existing_alert.id, "updated", None, 
                                 f"Missing items updated: {len(missing_items)} items")
            
            return existing_alert
        else:
            # Create new alert
            assigned_staff_id = self._get_assigned_staff_id(shelf_name)
            
            alert = Alert(
                alert_type=AlertType.MISPLACED_ITEM,
                priority=AlertPriority.LOW,
                status=AlertStatus.ACTIVE,
                shelf_name=shelf_name,
                rack_name=None,
                product_number=None,
                product_name=None,
                category=None,
                title=title,
                message=message,
                expected_product=", ".join(missing_items),
                actual_product=None,
                correct_location=None,
                assigned_staff_id=assigned_staff_id,
                created_by="system"
            )
            
            self.db.add(alert)
            self.db.flush()
            
            self._log_alert_action(alert.id, "created", None, 
                                 f"Missing items alert created: {len(missing_items)} items")
            
            return alert
    
    def _create_unknown_shelf_alert(self, shelf_number: str, items_detected: List[str]) -> Optional[Alert]:
        """Create alert for unknown shelf"""
        
        title = f"❓ UNKNOWN SHELF: {shelf_number}"
        message = f"Shelf {shelf_number} not found in inventory system."
        
        if items_detected:
            message += f" Detected items: {', '.join(items_detected)}"
        
        alert = Alert(
            alert_type=AlertType.MISPLACED_ITEM,
            priority=AlertPriority.LOW,
            status=AlertStatus.PENDING,
            shelf_name=shelf_number,
            rack_name=None,
            product_number=None,
            product_name=None,
            category=None,
            title=title,
            message=message,
            actual_product=", ".join(items_detected) if items_detected else None,
            assigned_staff_id=None,
            created_by="system"
        )
        
        self.db.add(alert)
        self.db.flush()
        
        self._log_alert_action(alert.id, "created", None, 
                             f"Unknown shelf alert: {shelf_number}")
        
        return alert
    
    def _find_correct_location(self, item_name: str) -> Optional[str]:
        """Find correct location for misplaced item"""
        
        # Search for item in inventory
        inventory_items = self.db.query(Inventory).filter(
            Inventory.product_name.ilike(f"%{item_name}%")
        ).all()
        
        if inventory_items:
            return inventory_items[0].shelf_name  # Return shelf name only
        
        return None
    
    def _resolve_existing_stock_alerts(self, shelf_name: str):
        """Resolve existing stock alerts when stock is back to normal"""
        
        existing_alerts = self.db.query(Alert).filter(
            and_(
                Alert.shelf_name == shelf_name,
                Alert.rack_name.is_(None),
                Alert.status == AlertStatus.ACTIVE,
                Alert.alert_type.in_([AlertType.LOW_STOCK, AlertType.MEDIUM_STOCK, 
                                    AlertType.HIGH_STOCK, AlertType.CRITICAL_STOCK, 
                                    AlertType.OUT_OF_STOCK])
            )
        ).all()
        
        for alert in existing_alerts:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            self._log_alert_action(alert.id, "auto_resolved", None, 
                                 "Stock level returned to normal")
    
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