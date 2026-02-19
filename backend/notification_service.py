from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from models import Notification, Task, NotificationStatus, TaskStatus
from calendar_service import CalendarService
from config import settings


class NotificationService:
    """Service for managing notifications and task acknowledgments."""
    
    def __init__(self, db: Session):
        self.db = db
        self.calendar_service = CalendarService(db)
    
    def create_notification(
        self, 
        task: Task, 
        scheduled_time: datetime = None
    ) -> Notification:
        """Create a notification for a task."""
        if scheduled_time is None:
            # Schedule notification 15 minutes before task
            scheduled_time = task.scheduled_date - timedelta(
                minutes=settings.notification_check_interval_minutes
            )
        
        message = f"Time to work on: {task.title}"
        if task.description:
            message += f"\n{task.description}"
        
        notification = Notification(
            task_id=task.id,
            message=message,
            scheduled_time=scheduled_time,
            status=NotificationStatus.PENDING
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        return notification
    
    def get_pending_notifications(self) -> List[Notification]:
        """Get all pending notifications that should be sent."""
        now = datetime.now()
        return self.db.query(Notification).filter(
            Notification.status == NotificationStatus.PENDING,
            Notification.scheduled_time <= now
        ).all()
    
    def send_notification(self, notification: Notification) -> bool:
        """Mark notification as sent."""
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now()
        self.db.commit()
        
        # In a real implementation, this would send push notification,
        # email, SMS, etc.
        print(f"[NOTIFICATION] {notification.message}")
        
        return True
    
    def acknowledge_notification(
        self, 
        notification_id: int, 
        acknowledged: bool = True
    ) -> dict:
        """Acknowledge or dismiss a notification."""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
        
        if not notification:
            return {"success": False, "message": "Notification not found"}
        
        task = notification.task
        
        if acknowledged:
            # User acknowledged - mark task as in progress
            notification.status = NotificationStatus.ACKNOWLEDGED
            notification.acknowledged_at = datetime.now()
            task.status = TaskStatus.IN_PROGRESS
            
            self.db.commit()
            
            return {
                "success": True, 
                "message": "Task started successfully",
                "task_id": task.id
            }
        else:
            # User didn't acknowledge - reschedule task
            notification.status = NotificationStatus.MISSED
            task.status = TaskStatus.MISSED
            
            self.db.commit()
            
            # Reschedule the task
            new_event = self.calendar_service.reschedule_task(task, "not_acknowledged")
            
            if new_event:
                # Create new notification for rescheduled task
                self.create_notification(task)
                
                return {
                    "success": True,
                    "message": f"Task rescheduled to {task.scheduled_date.strftime('%Y-%m-%d %H:%M')}",
                    "task_id": task.id,
                    "new_time": task.scheduled_date
                }
            else:
                return {
                    "success": False,
                    "message": "Could not find available slot to reschedule",
                    "task_id": task.id
                }
    
    def check_missed_tasks(self) -> List[Task]:
        """Check for tasks that were not acknowledged and need rescheduling."""
        # Find tasks with sent but unacknowledged notifications
        now = datetime.now()
        grace_period = timedelta(minutes=settings.notification_check_interval_minutes)
        
        missed_notifications = self.db.query(Notification).filter(
            Notification.status == NotificationStatus.SENT,
            Notification.sent_at < now - grace_period
        ).all()
        
        rescheduled_tasks = []
        
        for notification in missed_notifications:
            task = notification.task
            
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS]:
                # Mark as missed and reschedule
                notification.status = NotificationStatus.MISSED
                task.status = TaskStatus.MISSED
                
                new_event = self.calendar_service.reschedule_task(task, "timeout")
                
                if new_event:
                    # Create new notification
                    self.create_notification(task)
                    rescheduled_tasks.append(task)
        
        self.db.commit()
        
        return rescheduled_tasks
    
    def complete_task(self, task_id: int) -> dict:
        """Mark a task as completed."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            return {"success": False, "message": "Task not found"}
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        
        # Mark any pending notifications as acknowledged
        pending_notifications = self.db.query(Notification).filter(
            Notification.task_id == task_id,
            Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT])
        ).all()
        
        for notification in pending_notifications:
            notification.status = NotificationStatus.ACKNOWLEDGED
            notification.acknowledged_at = datetime.now()
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Task completed successfully",
            "task_id": task_id
        }
