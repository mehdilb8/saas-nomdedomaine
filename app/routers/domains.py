"""
Domain API Routes - CRUD operations and domain management
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.models import Domain, CheckLog, Notification, DomainStatus
from app.schemas import (
    DomainCreate,
    DomainUpdate,
    DomainResponse,
    DomainList,
    DomainWithLogs,
    CheckLogResponse,
    StatsResponse,
    HealthResponse
)
from app.config import settings
from app.services.availability import availability_service
from app.services.notification import notification_service
from app.services.scheduler import scheduler_service
from app.services.dns_checker import dns_checker


router = APIRouter(prefix="/api", tags=["domains"])


# ============================================
# HEALTH & STATS ENDPOINTS
# ============================================

@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint for Docker and monitoring

    Returns:
        Health status with database connection check
    """
    try:
        # Test database connection
        await db.execute(select(1))
        database_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        database_status = "disconnected"

    return HealthResponse(
        status="healthy" if database_status == "connected" else "unhealthy",
        database=database_status,
        timestamp=datetime.utcnow()
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get global statistics

    Returns:
        Statistics about domains, checks, and notifications
    """
    # Total domains
    total_result = await db.execute(select(func.count(Domain.id)))
    total_domains = total_result.scalar()

    # Active domains
    active_result = await db.execute(
        select(func.count(Domain.id)).where(Domain.is_active == True)
    )
    active_domains = active_result.scalar()

    # By status
    status_result = await db.execute(
        select(Domain.status, func.count(Domain.id))
        .group_by(Domain.status)
    )
    by_status = {status.value: count for status, count in status_result.all()}

    # By TLD
    tld_result = await db.execute(
        select(Domain.tld, func.count(Domain.id))
        .group_by(Domain.tld)
    )
    by_tld = {tld: count for tld, count in tld_result.all()}

    # Last check cycle (most recent last_checked)
    last_check_result = await db.execute(
        select(func.max(Domain.last_checked))
    )
    last_check_cycle = last_check_result.scalar()

    # Next check cycle
    next_check_cycle = scheduler_service.get_next_run_time()

    # Notifications today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    notif_result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.sent_at >= today_start)
        .where(Notification.success == True)
    )
    notifications_today = notif_result.scalar()

    return StatsResponse(
        total_domains=total_domains,
        active_domains=active_domains,
        by_status=by_status,
        by_tld=by_tld,
        last_check_cycle=last_check_cycle,
        next_check_cycle=next_check_cycle,
        notifications_today=notifications_today
    )


# ============================================
# DOMAIN CRUD ENDPOINTS
# ============================================

@router.get("/domains", response_model=DomainList)
async def list_domains(
    status: Optional[str] = Query(None, description="Filter by status (available, unavailable, unknown)"),
    tld: Optional[str] = Query(None, description="Filter by TLD (fr, com, net)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in domain name"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: str = Query("created_at", description="Sort field (created_at, last_checked, domain)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all domains with filters and pagination

    Args:
        status: Filter by availability status
        tld: Filter by TLD
        is_active: Filter by monitoring status
        search: Search term for domain name
        limit: Results per page
        offset: Pagination offset
        sort_by: Field to sort by
        sort_order: Sort direction

    Returns:
        Paginated list of domains
    """
    # Build query
    query = select(Domain)

    # Apply filters
    if status:
        try:
            status_enum = DomainStatus(status)
            query = query.where(Domain.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if tld:
        query = query.where(Domain.tld == tld.lower())

    if is_active is not None:
        query = query.where(Domain.is_active == is_active)

    if search:
        query = query.where(Domain.domain.contains(search.lower()))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting
    if sort_by == "domain":
        sort_column = Domain.domain
    elif sort_by == "last_checked":
        sort_column = Domain.last_checked
    else:
        sort_column = Domain.created_at

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute
    result = await db.execute(query)
    domains = result.scalars().all()

    return DomainList(
        total=total,
        limit=limit,
        offset=offset,
        domains=[DomainResponse.model_validate(d) for d in domains]
    )


@router.get("/domains/{domain_id}", response_model=DomainWithLogs)
async def get_domain(domain_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get domain details with recent check logs

    Args:
        domain_id: Domain ID

    Returns:
        Domain details with 10 most recent checks
    """
    # Get domain
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Get recent checks (last 10)
    checks_result = await db.execute(
        select(CheckLog)
        .where(CheckLog.domain_id == domain_id)
        .order_by(CheckLog.checked_at.desc())
        .limit(10)
    )
    checks = checks_result.scalars().all()

    # Build response
    domain_dict = DomainResponse.model_validate(domain).model_dump()
    domain_dict["recent_checks"] = [CheckLogResponse.model_validate(c) for c in checks]

    return DomainWithLogs(**domain_dict)


@router.post("/domains", response_model=DomainResponse, status_code=201)
async def create_domain(
    domain_data: DomainCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new domain to monitor

    Args:
        domain_data: Domain creation data

    Returns:
        Created domain
    """
    # Validate TLD
    if not dns_checker.is_supported_tld(domain_data.domain):
        tld = dns_checker.extract_tld(domain_data.domain)
        raise HTTPException(
            status_code=400,
            detail=f"TLD '{tld}' is not supported. Supported TLDs: {', '.join(settings.supported_tlds_list)}"
        )

    # Check if domain already exists
    existing = await db.execute(
        select(Domain).where(Domain.domain == domain_data.domain.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Domain already exists")

    # Extract TLD
    tld = dns_checker.extract_tld(domain_data.domain)

    # Create domain
    domain = Domain(
        domain=domain_data.domain.lower(),
        tld=tld,
        niche=domain_data.niche,
        traffic=domain_data.traffic or 0,
        referring_domains=domain_data.referring_domains or 0,
        status=DomainStatus.UNKNOWN,
        previous_status=DomainStatus.UNKNOWN,
        is_active=True
    )

    db.add(domain)
    await db.commit()
    await db.refresh(domain)

    logger.info(f"✅ Created new domain: {domain.domain} (ID: {domain.id})")

    return DomainResponse.model_validate(domain)


@router.put("/domains/{domain_id}", response_model=DomainResponse)
async def update_domain(
    domain_id: int,
    domain_data: DomainUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update domain metadata

    Args:
        domain_id: Domain ID
        domain_data: Update data

    Returns:
        Updated domain
    """
    # Get domain
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Update fields
    if domain_data.niche is not None:
        domain.niche = domain_data.niche
    if domain_data.traffic is not None:
        domain.traffic = domain_data.traffic
    if domain_data.referring_domains is not None:
        domain.referring_domains = domain_data.referring_domains

    await db.commit()
    await db.refresh(domain)

    logger.info(f"✅ Updated domain: {domain.domain} (ID: {domain.id})")

    return DomainResponse.model_validate(domain)


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_domain(domain_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a domain

    Args:
        domain_id: Domain ID
    """
    # Get domain
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    domain_name = domain.domain

    # Delete (cascade will handle check_logs and notifications)
    await db.execute(delete(Domain).where(Domain.id == domain_id))
    await db.commit()

    logger.info(f"🗑️ Deleted domain: {domain_name} (ID: {domain_id})")


@router.post("/domains/{domain_id}/check", response_model=DomainResponse)
async def force_check(domain_id: int, db: AsyncSession = Depends(get_db)):
    """
    Force immediate verification of a domain

    Args:
        domain_id: Domain ID

    Returns:
        Updated domain after check
    """
    # Get domain
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    logger.info(f"🔍 Forcing check for domain: {domain.domain}")

    # Verify domain
    verification_result = await availability_service.verify_domain(domain, db)

    # Save check logs
    await availability_service.save_check_logs(
        domain_id=domain.id,
        check_logs=verification_result.check_logs,
        db=db
    )

    # Send notification if needed
    if verification_result.should_notify:
        await notification_service.send_discord_notification(domain, db)

    await db.refresh(domain)

    return DomainResponse.model_validate(domain)


@router.patch("/domains/{domain_id}/toggle", response_model=DomainResponse)
async def toggle_monitoring(domain_id: int, db: AsyncSession = Depends(get_db)):
    """
    Toggle domain monitoring (active/inactive)

    Args:
        domain_id: Domain ID

    Returns:
        Updated domain
    """
    # Get domain
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()

    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Toggle
    domain.is_active = not domain.is_active

    await db.commit()
    await db.refresh(domain)

    status = "activated" if domain.is_active else "deactivated"
    logger.info(f"🔄 Monitoring {status} for domain: {domain.domain}")

    return DomainResponse.model_validate(domain)
