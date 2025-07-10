from typing import List, Dict, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.alert import Alert, AlertType, AlertStatus, AlertPriority
from app.models.inventory import Inventory
from app.models.shelf import Shelf
from app.models.staff_assignment import StaffAssignment
from app.models.employee import Employee
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
    
    def process_shelf_data(self, shelf_data: Dict) -> List[Alert]:
        """Process JSON shelf data and generate alerts"""
        alerts = []
        
        try:
            for shelf in shelf_data.get("shelves", []):
                shelf_id = shelf.get("shelf_id", "")
                
                # Get shelf from database
                db_shelf = self.db.query(Shelf).filter(Shelf.name == shelf_id).first()
                if not db_shelf:
                    logger.warning(f"Shelf {shelf_id} not found in database")
                    continue
                
                # Process each rack in the shelf
                for rack_data in shelf.get("racks", []):
                    rack_alerts = self._process_rack_data(shelf_id, rack_data, db_shelf)
                    alerts.extend(rack_alerts)
            
            logger.info(f"Processed {len(alerts)} alerts from shelf data")
            return alerts
            
        except Exception as e:
            logger.error(f"Error processing shelf data: {str(e)}")
            return []
    
    def _process_rack_data(self, shelf_name: str, rack_data: Dict, db_shelf: Shelf) -> List[Alert]:
        """Process individual rack data and generate alerts"""
        alerts = []
        
        try:
            rack_id = rack_data.get("rack_id", "")
            item_from_json = rack_data.get("item", "")
            empty_percentage = rack_data.get("class_coverage", {}).get("empty", 0.0)
            disordered_percentage = rack_data.get("class_coverage", {}).get("disordered", 0.0)
            
            # Extract rack name from rack_id (e.g., "S1-R1" -> "R1")
            rack_name = rack_id.split("-")[-1] if "-" in rack_id else rack_id
            
            # Calculate fill percentage
            fill_percentage = 100 - empty_percentage
            
            # Get inventory item for this shelf and rack
            inventory_item = self.db.query(Inventory).filter(
                and_(
                    Inventory.shelf_name == shelf_name,
                    Inventory.rack_name == rack_name
                )
            ).first()
            
            # Check for stock level alerts
            stock_alert = self._check_stock_levels(
                shelf_name, rack_name, inventory_item, empty_percentage, fill_percentage
            )
            if stock_alert:
                alerts.append(stock_alert)
            
            # Check for misplacement alerts
            misplacement_alert = self._check_misplacement(
                shelf_name, rack_name, item_from_json, inventory_item, disordered_percentage
            )
            if misplacement_alert:
                alerts.append(misplacement_alert)
            
        except Exception as e:
            logger.error(f"Error processing rack data for {shelf_name}: {str(e)}")
        
        return alerts
    
    def _check_stock_levels(self, shelf_name: str, rack_name: str, 
                           inventory_item: Inventory, empty_percentage: float, 
                           fill_percentage: float) -> Optional[Alert]:
        """Check stock levels and create appropriate alerts"""
        
        if not inventory_item:
            return None
        
        # Determine alert type, priority and message based on fill percentage
        alert_type = None
        priority = None
        title = ""
        message = ""
        
        if fill_percentage == 0:
            alert_type = AlertType.CRITICAL_STOCK
            priority = AlertPriority.CRITICAL
            title = f"🚨 CRITICAL: {inventory_item.product_name} - EMPTY"
            message = f"Product '{inventory_item.product_name}' (#{inventory_item.product_number}) is completely empty on shelf {shelf_name}, rack {rack_name}. IMMEDIATE REFILL REQUIRED!"
        elif fill_percentage <= 10:
            alert_type = AlertType.HIGH_STOCK
            priority = AlertPriority.HIGH
            title = f"🔴 HIGH: {inventory_item.product_name} - {fill_percentage:.1f}% filled"
            message = f"Product '{inventory_item.product_name}' on {shelf_name}-{rack_name} is critically low at {fill_percentage:.1f}% filled. Urgent restocking needed!"
        elif fill_percentage <= 25:
            alert_type = AlertType.MEDIUM_STOCK
            priority = AlertPriority.MEDIUM
            title = f"🟡 MEDIUM: {inventory_item.product_name} - {fill_percentage:.1f}% filled"
            message = f"Product '{inventory_item.product_name}' on {shelf_name}-{rack_name} is at {fill_percentage:.1f}% capacity. Restocking recommended."
        elif fill_percentage <= 40:
            alert_type = AlertType.LOW_STOCK
            priority = AlertPriority.LOW
            title = f"🟢 LOW: {inventory_item.product_name} - {fill_percentage:.1f}% filled"
            message = f"Product '{inventory_item.product_name}' on {shelf_name}-{rack_name} is at {fill_percentage:.1f}% capacity. Monitor for restocking."
        
        if alert_type:
            # Check if similar active alert exists (within last 1 hour to avoid spam)
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            existing_alert = self.db.query(Alert).filter(
                and_(
                    Alert.shelf_name == shelf_name,
                    Alert.rack_name == rack_name,
                    Alert.alert_type == alert_type,
                    Alert.status == AlertStatus.ACTIVE,
                    Alert.created_at > one_hour_ago
                )
            ).first()
            
            if existing_alert:
                # Update existing alert
                existing_alert.title = title
                existing_alert.message = message
                existing_alert.empty_percentage = empty_percentage
                existing_alert.fill_percentage = fill_percentage
                existing_alert.updated_at = datetime.utcnow()
                self.db.commit()
                return existing_alert
            else:
                # Create new alert
                assigned_staff_id = self._get_assigned_staff_id(shelf_name)
                
                alert = Alert(
                    alert_type=alert_type,
                    priority=priority,
                    shelf_name=shelf_name,
                    rack_name=rack_name,
                    product_number=inventory_item.product_number,
                    product_name=inventory_item.product_name,
                    category=inventory_item.category,
                    title=title,
                    message=message,
                    empty_percentage=empty_percentage,
                    fill_percentage=fill_percentage,
                    assigned_staff_id=assigned_staff_id
                )
                
                self.db.add(alert)
                self.db.commit()
                self.db.refresh(alert)
                
                # Send notifications
                self._send_alert_notifications(alert)
                
                return alert
        
        return None
    
    def _check_misplacement(self, shelf_name: str, rack_name: str, 
                           item_from_json: str, inventory_item: Inventory,
                           disordered_percentage: float) -> Optional[Alert]:
        """Check for misplaced items"""
        
        if not inventory_item:
            return None
        
        # Check if detected item matches expected item
        expected_product = inventory_item.product_name.lower()
        detected_item = item_from_json.lower()
        
        # Simple matching logic (you can enhance this)
        is_misplaced = False
        
        # Check if detected item name doesn't match expected product
        if detected_item not in expected_product and expected_product not in detected_item:
            is_misplaced = True
        
        # Also consider high disordered percentage as potential misplacement
        if disordered_percentage > 15:  # Threshold for disorder
            is_misplaced = True
        
        if is_misplaced:
            # Find correct location for the detected item
            correct_location = self._find_correct_location(item_from_json, inventory_item.category)
            
            title = f"🔄 MISPLACED: {item_from_json} on {shelf_name}-{rack_name}"
            message = f"Wrong item '{item_from_json}' detected on {shelf_name}-{rack_name}. Expected: '{inventory_item.product_name}'"
            
            if correct_location:
                message += f" | Correct location for '{item_from_json}': {correct_location}"
            else:
                message += f" | Item '{item_from_json}' not registered in system"
            
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
                existing_alert.actual_product = item_from_json
                existing_alert.expected_product = inventory_item.product_name
                existing_alert.correct_location = correct_location
                existing_alert.updated_at = datetime.utcnow()
                self.db.commit()
                return existing_alert
            else:
                # Create new alert
                assigned_staff_id = self._get_assigned_staff_id(shelf_name)
                
                alert = Alert(
                    alert_type=AlertType.MISPLACED_ITEM,
                    priority=AlertPriority.MEDIUM,
                    shelf_name=shelf_name,
                    rack_name=rack_name,
                    product_number=inventory_item.product_number,
                    product_name=inventory_item.product_name,
                    category=inventory_item.category,
                    title=title,
                    message=message,
                    expected_product=inventory_item.product_name,
                    actual_product=item_from_json,
                    correct_location=correct_location,
                    assigned_staff_id=assigned_staff_id
                )
                
                self.db.add(alert)
                self.db.commit()
                self.db.refresh(alert)
                
                # Send notifications
                self._send_alert_notifications(alert)
                
                return alert
        
        return None
    
    def _find_correct_location(self, item_name: str, category: str) -> Optional[str]:
        """Find correct location for misplaced item"""
        
        # Search for item in inventory by name pattern and category
        items = self.db.query(Inventory).filter(
            and_(
                Inventory.product_name.ilike(f"%{item_name}%"),
                Inventory.category == category
            )
        ).all()
        
        if items:
            item = items[0]  # Take first match
            return f"{item.shelf_name}-{item.rack_name}"
        
        # If not found in same category, search in all categories
        items = self.db.query(Inventory).filter(
            Inventory.product_name.ilike(f"%{item_name}%")
        ).all()
        
        if items:
            item = items[0]
            return f"{item.shelf_name}-{item.rack_name}"
        
        return None
    
    def _get_assigned_staff_id(self, shelf_name: str) -> Optional[int]:
        """Get assigned staff ID for a shelf"""
        
        # Get shelf ID
        shelf = self.db.query(Shelf).filter(Shelf.name == shelf_name).first()
        if not shelf:
            return None
        
        # Get active staff assignment
        assignment = self.db.query(StaffAssignment).filter(
            and_(
                StaffAssignment.shelf_id == shelf.id,
                StaffAssignment.is_active == True
            )
        ).first()
        
        return assignment.employee_id if assignment else None
    
    def _send_alert_notifications(self, alert: Alert):
        """Send notifications for alert"""
        
        notified_staff_ids = []
        
        # Send to assigned staff
        if alert.assigned_staff_id:
            staff = self.db.query(Employee).filter(
                Employee.id == alert.assigned_staff_id
            ).first()
            if staff and staff.is_active:
                self.notification_service.send_staff_notification(staff, alert)
                self.websocket_service.send_alert_to_user(staff.id, alert)
                notified_staff_ids.append(staff.id)
        
        # Send to all store managers
        managers = self.db.query(Employee).filter(
            and_(
                Employee.role == "store_manager",
                Employee.is_active == True
            )
        ).all()
        
        for manager in managers:
            self.notification_service.send_manager_notification(manager, alert)
            self.websocket_service.send_alert_to_user(manager.id, alert)
            notified_staff_ids.append(manager.id)
        
        # Update alert with notified staff IDs
        alert.notified_staff_ids = json.dumps(notified_staff_ids)
        self.db.commit()
    
    def get_active_alerts(self, employee_id: Optional[int] = None, 
                         shelf_name: Optional[str] = None) -> List[Alert]:
        """Get active alerts for dashboard"""
        
        query = self.db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE)
        
        if employee_id:
            # Get alerts assigned to this employee or if they're a manager
            employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
            if employee and employee.role != "store_manager":
                query = query.filter(Alert.assigned_staff_id == employee_id)
        
        if shelf_name:
            query = query.filter(Alert.shelf_name == shelf_name)
        
        return query.order_by(Alert.priority.desc(), Alert.created_at.desc()).all()
    
    def get_alert_statistics(self) -> Dict:
        """Get alert statistics for dashboard"""
        
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
        
        # Alerts by type
        stock_alerts = self.db.query(Alert).filter(
            and_(
                Alert.status == AlertStatus.ACTIVE,
                Alert.alert_type.in_([AlertType.LOW_STOCK, AlertType.MEDIUM_STOCK, 
                                    AlertType.HIGH_STOCK, AlertType.CRITICAL_STOCK])
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
    
    def acknowledge_alert(self, alert_id: int, employee_id: int) -> bool:
        """Acknowledge an alert"""
        
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Send WebSocket update
            self.websocket_service.send_alert_update(alert)
            
            return True
        return False
    
    def resolve_alert(self, alert_id: int, employee_id: int) -> bool:
        """Resolve an alert"""
        
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Send WebSocket update
            self.websocket_service.send_alert_update(alert)
            
            return True
        return False
    
    def get_alert_history(self, shelf_name: Optional[str] = None, 
                         days: int = 30) -> List[Alert]:
        """Get alert history"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        query = self.db.query(Alert).filter(Alert.created_at >= start_date)
        
        if shelf_name:
            query = query.filter(Alert.shelf_name == shelf_name)
        
        return query.order_by(Alert.created_at.desc()).all()

