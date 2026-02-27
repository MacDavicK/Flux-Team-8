from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

class GoalStatus(enum.Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    PAUSED = 'paused'

class TaskStatus(enum.Enum):
    SCHEDULED = 'scheduled'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    RESCHEDULED = 'rescheduled'
    MISSED = 'missed'

class Goal(Base):
    __tablename__ = 'goals'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    due_date = Column(DateTime, nullable=False)
    status = Column(SQLEnum(GoalStatus), default=GoalStatus.PENDING)
    ai_analysis = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    milestones = relationship('Milestone', back_populates='goal', cascade='all, delete-orphan')
    tasks = relationship('Task', back_populates='goal', cascade='all, delete-orphan')

class Milestone(Base):
    __tablename__ = 'milestones'
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey('goals.id'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    week_number = Column(Integer, nullable=False)
    target_date = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    goal = relationship('Goal', back_populates='milestones')
    tasks = relationship('Task', back_populates='milestone')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey('goals.id'), nullable=False)
    milestone_id = Column(Integer, ForeignKey('milestones.id'))
    title = Column(String, nullable=False)
    description = Column(Text)
    scheduled_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.SCHEDULED)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    goal = relationship('Goal', back_populates='tasks')
    milestone = relationship('Milestone', back_populates='tasks')
    calendar_event = relationship('CalendarEvent', back_populates='task', uselist=False)
    notifications = relationship('Notification', back_populates='task')

class CalendarEvent(Base):
    __tablename__ = 'calendar_events'
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    event_id = Column(String)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    task = relationship('Task', back_populates='calendar_event')

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    sent = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    task = relationship('Task', back_populates='notifications')

