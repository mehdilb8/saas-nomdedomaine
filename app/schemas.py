"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class DomainStatus(str, Enum):
    """Domain availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class CheckStatus(str, Enum):
    """Check result status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


# ============================================
# DOMAIN SCHEMAS
# ============================================

class DomainCreate(BaseModel):
    """Schema for creating a new domain"""
    domain: str = Field(..., min_length=3, max_length=255, description="Full domain name (e.g., example.fr)")
    niche: Optional[str] = Field(None, max_length=100, description="Domain niche or category")
    traffic: Optional[int] = Field(0, ge=0, description="Estimated monthly traffic")
    referring_domains: Optional[int] = Field(0, ge=0, description="Number of referring domains")

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain format"""
        v = v.lower().strip()
        if not v or '.' not in v:
            raise ValueError("Invalid domain format")
        # Basic validation - domain should have at least one dot
        parts = v.split('.')
        if len(parts) < 2:
            raise ValueError("Domain must have at least one extension")
        return v


class DomainUpdate(BaseModel):
    """Schema for updating a domain"""
    niche: Optional[str] = Field(None, max_length=100)
    traffic: Optional[int] = Field(None, ge=0)
    referring_domains: Optional[int] = Field(None, ge=0)


class DomainResponse(BaseModel):
    """Schema for domain response"""
    id: int
    domain: str
    tld: str
    niche: Optional[str]
    traffic: int
    referring_domains: int
    status: DomainStatus
    previous_status: DomainStatus
    last_checked: Optional[datetime]
    last_available: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DomainList(BaseModel):
    """Schema for paginated domain list"""
    total: int
    limit: int
    offset: int
    domains: List[DomainResponse]


# ============================================
# CHECK LOG SCHEMAS
# ============================================

class CheckLogResponse(BaseModel):
    """Schema for check log response"""
    id: int
    domain_id: int
    status_found: CheckStatus
    check_method: str
    response_time_ms: Optional[int]
    error_message: Optional[str]
    notification_sent: bool
    checked_at: datetime

    model_config = {"from_attributes": True}


class DomainWithLogs(DomainResponse):
    """Schema for domain with recent check logs"""
    recent_checks: List[CheckLogResponse] = []


# ============================================
# NOTIFICATION SCHEMAS
# ============================================

class NotificationResponse(BaseModel):
    """Schema for notification response"""
    id: int
    domain_id: int
    webhook_response: Optional[str]
    http_status: Optional[int]
    success: bool
    sent_at: datetime

    model_config = {"from_attributes": True}


# ============================================
# STATS SCHEMAS
# ============================================

class StatsResponse(BaseModel):
    """Schema for global statistics"""
    total_domains: int
    active_domains: int
    by_status: Dict[str, int]
    by_tld: Dict[str, int]
    last_check_cycle: Optional[datetime]
    next_check_cycle: Optional[datetime]
    notifications_today: int


# ============================================
# HEALTH CHECK SCHEMA
# ============================================

class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    database: str
    timestamp: datetime
