"""
SQLAlchemy models for domain monitoring
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, ForeignKey, Index
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class DomainStatus(str, enum.Enum):
    """Domain availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class CheckStatus(str, enum.Enum):
    """Check result status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class Domain(Base):
    """Domain model for tracking expired domains"""
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, unique=True, index=True)
    tld = Column(String(10), nullable=False, index=True)
    niche = Column(String(100), nullable=True)
    traffic = Column(Integer, default=0)
    referring_domains = Column(Integer, default=0)
    status = Column(Enum(DomainStatus), default=DomainStatus.UNKNOWN, index=True)
    previous_status = Column(Enum(DomainStatus), default=DomainStatus.UNKNOWN)
    last_checked = Column(DateTime, nullable=True, index=True)
    last_available = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_is_active', 'is_active'),
        Index('idx_status', 'status'),
        Index('idx_tld', 'tld'),
        Index('idx_last_checked', 'last_checked'),
    )


class CheckLog(Base):
    """Log of domain availability checks"""
    __tablename__ = "check_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey('domains.id', ondelete='CASCADE'), nullable=False, index=True)
    status_found = Column(Enum(CheckStatus), nullable=False, index=True)
    check_method = Column(String(20), nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    notification_sent = Column(Boolean, default=False)
    checked_at = Column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        Index('idx_domain_id', 'domain_id'),
        Index('idx_checked_at', 'checked_at'),
        Index('idx_status_found', 'status_found'),
    )


class Notification(Base):
    """Log of Discord notifications sent"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey('domains.id', ondelete='CASCADE'), nullable=False, index=True)
    webhook_response = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)
    success = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        Index('idx_domain_id', 'domain_id'),
        Index('idx_sent_at', 'sent_at'),
        Index('idx_success', 'success'),
    )
