from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from models import CalendarEvent, Task, TaskStatus
from config import settings


class CalendarService:
    """Service for managing calendar and scheduling."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_available_slots(
        self, 
        start_date: datetime, 
        end_date: datetime,
        duration_minutes: int = None
    ) -> List[Tuple[datetime, datetime]]:
        """Get available time slots in the calendar."""
        if duration_minutes is None:
            duration_minutes = settings.default_task_duration_minutes
        
        # Get all existing events in the date range
        existing_events = self.db.query(CalendarEvent).filter(
            CalendarEvent.start_time >= start_date,
            CalendarEvent.end_time <= end_date
        ).order_by(CalendarEvent.start_time).all()
        
        available_slots = []
        current_date = start_date.date()
        end_search_date = end_date.date()
        
        while current_date <= end_search_date:
            # Define working hours for each day
            work_start = datetime.combine(
                current_date, 
                datetime.min.time().replace(hour=settings.default_work_start_hour)
            )
            work_end = datetime.combine(
                current_date, 
                datetime.min.time().replace(hour=settings.default_work_end_hour)
            )
            
            # Get events for this day
            day_events = [
                e for e in existing_events 
                if e.start_time.date() == current_date
            ]
            
            if not day_events:
                # Entire day is free
                current_time = work_start
                while current_time + timedelta(minutes=duration_minutes) <= work_end:
                    slot_end = current_time + timedelta(minutes=duration_minutes)
                    available_slots.append((current_time, slot_end))
                    current_time += timedelta(minutes=duration_minutes)
            else:
                # Find gaps between events
                current_time = work_start
                
                for event in day_events:
                    # Check gap before this event
                    if current_time < event.start_time:
                        while current_time + timedelta(minutes=duration_minutes) <= event.start_time:
                            slot_end = current_time + timedelta(minutes=duration_minutes)
                            available_slots.append((current_time, slot_end))
                            current_time += timedelta(minutes=duration_minutes)
                    
                    current_time = max(current_time, event.end_time)
                
                # Check gap after last event
                while current_time + timedelta(minutes=duration_minutes) <= work_end:
                    slot_end = current_time + timedelta(minutes=duration_minutes)
                    available_slots.append((current_time, slot_end))
                    current_time += timedelta(minutes=duration_minutes)
            
            current_date += timedelta(days=1)
        
        return available_slots
    
    def schedule_task(
        self, 
        task: Task, 
        preferred_date: datetime
    ) -> Optional[CalendarEvent]:
        """Schedule a task on the calendar."""
        # Check if preferred time is available
        duration = timedelta(minutes=task.duration_minutes)
        end_time = preferred_date + duration
        
        # Check for conflicts
        conflict = self.db.query(CalendarEvent).filter(
            CalendarEvent.start_time < end_time,
            CalendarEvent.end_time > preferred_date
        ).first()
        
        if conflict:
            # Find next available slot
            available_slots = self.get_available_slots(
                preferred_date,
                preferred_date + timedelta(days=7),
                task.duration_minutes
            )
            
            if not available_slots:
                return None
            
            # Use first available slot
            preferred_date, end_time = available_slots[0]
        
        # Create calendar event
        event = CalendarEvent(
            task_id=task.id,
            title=task.title,
            description=task.description,
            start_time=preferred_date,
            end_time=end_time,
            is_task_related=True
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        return event
    
    def reschedule_task(
        self, 
        task: Task, 
        reason: str = "missed"
    ) -> Optional[CalendarEvent]:
        """Reschedule a missed or unacknowledged task."""
        # Delete existing calendar event
        if task.calendar_event:
            self.db.delete(task.calendar_event)
        
        # Calculate new date based on reschedule strategy
        original_date = task.scheduled_date
        days_to_add = settings.missed_task_reschedule_days
        
        # Find next available slot
        search_start = datetime.now() + timedelta(days=days_to_add)
        search_end = search_start + timedelta(days=7)
        
        available_slots = self.get_available_slots(
            search_start,
            search_end,
            task.duration_minutes
        )
        
        if not available_slots:
            # Try next week
            search_start += timedelta(days=7)
            search_end += timedelta(days=7)
            available_slots = self.get_available_slots(
                search_start,
                search_end,
                task.duration_minutes
            )
        
        if not available_slots:
            return None
        
        # Schedule at first available slot
        new_start_time = available_slots[0][0]
        
        # Update task
        if task.original_date is None:
            task.original_date = original_date
        
        task.scheduled_date = new_start_time
        task.reschedule_count += 1
        task.status = TaskStatus.RESCHEDULED
        
        # Create new calendar event
        event = self.schedule_task(task, new_start_time)
        
        self.db.commit()
        
        return event
    
    def get_events(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[CalendarEvent]:
        """Get all calendar events in a date range."""
        return self.db.query(CalendarEvent).filter(
            CalendarEvent.start_time >= start_date,
            CalendarEvent.end_time <= end_date
        ).order_by(CalendarEvent.start_time).all()
