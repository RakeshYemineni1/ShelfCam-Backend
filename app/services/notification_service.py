# app/services/notification_service.py
from typing import List
from app.models.employee import Employee
from app.models.alert import Alert
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', 'alerts@shelfcam.com')
    
    def send_staff_notification(self, staff: Employee, alert: Alert):
        """Send notification to assigned staff"""
        
        priority_emoji = {
            "critical": "🚨",
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }
        
        subject = f"{priority_emoji.get(alert.priority.value, '📢')} ShelfCam Alert: {alert.title}"
        
        body = f"""
Dear {staff.username},

A new alert has been assigned to you:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️  Alert Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Alert Type: {alert.alert_type.value.replace('_', ' ').title()}
⚠️  Priority: {alert.priority.value.upper()}
🏪 Location: {alert.shelf_name} - {alert.rack_name}
📦 Product: {alert.product_name}
🔢 Product #: {alert.product_number}

💬 Message: {alert.message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Action Required
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please visit the location and take appropriate action:
• For stock alerts: Restock the item as needed
• For misplacement alerts: Reorganize items to correct positions

Don't forget to acknowledge this alert in your ShelfCam dashboard once resolved.

Best regards,
ShelfCam Alert System
Generated at: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self._send_email(staff.email, subject, body)
    
    def send_manager_notification(self, manager: Employee, alert: Alert):
        """Send notification to store manager"""
        
        subject = f"🏪 ShelfCam Management Alert: {alert.title}"
        
        assigned_staff_name = "Unassigned"
        if alert.assigned_staff:
            assigned_staff_name = alert.assigned_staff.username
        
        body = f"""
Dear Store Manager,

A new alert has been generated in your store:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️  Alert Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Alert Type: {alert.alert_type.value.replace('_', ' ').title()}
⚠️  Priority: {alert.priority.value.upper()}
🏪 Location: {alert.shelf_name} - {alert.rack_name}
📦 Product: {alert.product_name}
🔢 Product #: {alert.product_number}
👤 Assigned Staff: {assigned_staff_name}
💬 Details: {alert.message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Management Actions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Monitor alert resolution progress
• Ensure staff responds within appropriate timeframe
• Review alert patterns for operational improvements
• Access full details in your ShelfCam management dashboard

Best regards,
ShelfCam Management System

Generated at: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self._send_email(manager.email, subject, body)

    def send_bulk_notifications(self, alerts: List[Alert]):
        """Send notifications for multiple alerts"""
        for alert in alerts:
            try:
                # Send to assigned staff
                if alert.assigned_staff:
                    self.send_staff_notification(alert.assigned_staff, alert)
                
                # Send to store manager (get from shelf assignment)
                if hasattr(alert, 'shelf') and alert.shelf and alert.shelf.assigned_staff:
                    # Assuming manager is identified by role or specific field
                    manager = self._get_store_manager(alert.shelf.store_id)
                    if manager:
                        self.send_manager_notification(manager, alert)
                        
            except Exception as e:
                logger.error(f"Failed to send notification for alert {alert.id}: {str(e)}")

    def send_alert_history_summary(self, manager: Employee, store_id: int, period_days: int = 7):
        """Send periodic alert history summary to store manager"""
        from app.models.alert import Alert
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get alert statistics
        alert_stats = self._get_alert_statistics(store_id, start_date, end_date)
        
        subject = f"📊 ShelfCam Weekly Alert Summary - Store {store_id}"
        
        body = f"""
Dear Store Manager,

Here's your {period_days}-day alert summary:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Alert Statistics ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔢 Total Alerts: {alert_stats['total_alerts']}
✅ Resolved: {alert_stats['resolved_alerts']}
⏳ Pending: {alert_stats['pending_alerts']}
🚨 Critical: {alert_stats['critical_alerts']}
🔴 High Priority: {alert_stats['high_priority_alerts']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Alert Types Breakdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{self._format_alert_types_breakdown(alert_stats['alert_types'])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 Staff Performance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{self._format_staff_performance(alert_stats['staff_performance'])}

For detailed analysis, please visit your ShelfCam management dashboard.

Best regards,
ShelfCam Analytics System
"""
        
        self._send_email(manager.email, subject, body)

    def _send_email(self, to_email: str, subject: str, body: str):
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise

    def _get_store_manager(self, store_id: int) -> Employee:
        """Get store manager for a specific store"""
        from app.models.employee import Employee
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Assuming manager role is identified by role field
            manager = db.query(Employee).filter(
                Employee.store_id == store_id,
                Employee.role == 'manager'
            ).first()
            return manager
        finally:
            db.close()

    def _get_alert_statistics(self, store_id: int, start_date, end_date):
        """Get alert statistics for a store within date range"""
        from app.models.alert import Alert
        from app.database import SessionLocal
        from sqlalchemy import func
        
        db = SessionLocal()
        try:
            # Get alerts for the store within date range
            alerts_query = db.query(Alert).filter(
                Alert.store_id == store_id,
                Alert.created_at >= start_date,
                Alert.created_at <= end_date
            )
            
            total_alerts = alerts_query.count()
            resolved_alerts = alerts_query.filter(Alert.status == 'resolved').count()
            pending_alerts = alerts_query.filter(Alert.status == 'pending').count()
            critical_alerts = alerts_query.filter(Alert.priority == 'critical').count()
            high_priority_alerts = alerts_query.filter(Alert.priority == 'high').count()
            
            # Alert types breakdown
            alert_types = db.query(
                Alert.alert_type,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.store_id == store_id,
                Alert.created_at >= start_date,
                Alert.created_at <= end_date
            ).group_by(Alert.alert_type).all()
            
            # Staff performance
            staff_performance = db.query(
                Employee.username,
                func.count(Alert.id).label('alerts_handled'),
                func.sum(func.case([(Alert.status == 'resolved', 1)], else_=0)).label('resolved_count')
            ).join(
                Alert, Alert.assigned_staff_id == Employee.id
            ).filter(
                Alert.store_id == store_id,
                Alert.created_at >= start_date,
                Alert.created_at <= end_date
            ).group_by(Employee.id, Employee.username).all()
            
            return {
                'total_alerts': total_alerts,
                'resolved_alerts': resolved_alerts,
                'pending_alerts': pending_alerts,
                'critical_alerts': critical_alerts,
                'high_priority_alerts': high_priority_alerts,
                'alert_types': alert_types,
                'staff_performance': staff_performance
            }
            
        finally:
            db.close()

    def _format_alert_types_breakdown(self, alert_types):
        """Format alert types for email display"""
        if not alert_types:
            return "No alerts recorded for this period."
        
        formatted_types = []
        for alert_type, count in alert_types:
            emoji = {
                'low_stock': '📦',
                'out_of_stock': '🚫',
                'misplaced_item': '🔄',
                'expired_product': '⏰'
            }.get(alert_type.value, '📋')
            
            formatted_types.append(f"{emoji} {alert_type.value.replace('_', ' ').title()}: {count}")
        
        return '\n'.join(formatted_types)

    def _format_staff_performance(self, staff_performance):
        """Format staff performance for email display"""
        if not staff_performance:
            return "No staff performance data available."
        
        formatted_performance = []
        for username, alerts_handled, resolved_count in staff_performance:
            resolution_rate = (resolved_count / alerts_handled * 100) if alerts_handled > 0 else 0
            formatted_performance.append(
                f"👤 {username}: {alerts_handled} alerts handled, {resolved_count} resolved ({resolution_rate:.1f}%)"
            )
        
        return '\n'.join(formatted_performance)