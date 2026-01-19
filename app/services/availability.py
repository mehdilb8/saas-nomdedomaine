"""
Availability Service - Orchestrate domain verification with double-check logic
"""
import asyncio
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.models import Domain, CheckLog, DomainStatus, CheckStatus
from app.services.dns_checker import dns_checker


@dataclass
class VerificationResult:
    """Result of domain verification"""
    is_available: bool
    should_notify: bool
    check_logs: List[dict]
    previous_status: str
    new_status: str


class AvailabilityService:
    """Service for verifying domain availability with double-check"""

    def __init__(self):
        self.double_check_delay = settings.double_check_delay_seconds
        self.primary_dns = settings.dns_primary_server
        self.secondary_dns = settings.dns_secondary_server

    async def verify_domain(
        self,
        domain: Domain,
        db: AsyncSession
    ) -> VerificationResult:
        """
        Verify domain availability with double-check logic

        Args:
            domain: Domain model instance
            db: Database session

        Returns:
            VerificationResult with availability status and notification flag

        Logic:
            1. Save previous_status
            2. First check with primary DNS
            3. If unavailable → return (no notification)
            4. If available → wait 5s → second check with secondary DNS
            5. If both available → detect transition → determine if notify
        """
        check_logs = []
        previous_status = domain.status

        logger.info(f"🔍 Starting verification for domain: {domain.domain}")

        # ============================================
        # FIRST CHECK - Primary DNS
        # ============================================
        logger.debug(f"First check for {domain.domain} using {self.primary_dns}")

        result1 = await dns_checker.check_domain_availability(
            domain.domain,
            self.primary_dns
        )

        # Log first check
        check_logs.append({
            "status_found": CheckStatus.AVAILABLE if result1.available else CheckStatus.UNAVAILABLE,
            "check_method": result1.method,
            "response_time_ms": result1.response_time_ms,
            "error_message": result1.error,
            "notification_sent": False
        })

        # If domain is NOT available, stop here
        if not result1.available:
            logger.info(f"❌ Domain {domain.domain} is UNAVAILABLE (first check)")

            # Update domain status
            domain.previous_status = previous_status
            domain.status = DomainStatus.UNAVAILABLE
            domain.last_checked = datetime.utcnow()

            await db.commit()

            return VerificationResult(
                is_available=False,
                should_notify=False,
                check_logs=check_logs,
                previous_status=previous_status.value,
                new_status=DomainStatus.UNAVAILABLE.value
            )

        # ============================================
        # DOUBLE CHECK - Wait + Secondary DNS
        # ============================================
        logger.debug(
            f"First check shows AVAILABLE, waiting {self.double_check_delay}s "
            f"before second check..."
        )
        await asyncio.sleep(self.double_check_delay)

        logger.debug(f"Second check for {domain.domain} using {self.secondary_dns}")

        result2 = await dns_checker.check_domain_availability(
            domain.domain,
            self.secondary_dns
        )

        # Log second check
        check_logs.append({
            "status_found": CheckStatus.AVAILABLE if result2.available else CheckStatus.UNAVAILABLE,
            "check_method": result2.method,
            "response_time_ms": result2.response_time_ms,
            "error_message": result2.error,
            "notification_sent": False
        })

        # ============================================
        # ANALYZE RESULTS
        # ============================================
        if result2.available:
            # Both checks confirm availability
            logger.success(f"✅ Domain {domain.domain} is AVAILABLE (double-checked)")

            # Update domain status
            domain.previous_status = previous_status
            domain.status = DomainStatus.AVAILABLE
            domain.last_checked = datetime.utcnow()
            domain.last_available = datetime.utcnow()

            # ============================================
            # DETERMINE IF NOTIFICATION NEEDED (ANTI-SPAM)
            # ============================================
            should_notify = False

            if previous_status != DomainStatus.AVAILABLE:
                # TRANSITION DETECTED: unavailable/unknown → available
                should_notify = True
                logger.info(
                    f"🔔 Transition detected for {domain.domain}: "
                    f"{previous_status.value} → available (WILL NOTIFY)"
                )
            else:
                # Already was available, don't spam
                logger.debug(
                    f"🔕 Domain {domain.domain} was already available "
                    f"(no notification needed)"
                )

            await db.commit()

            return VerificationResult(
                is_available=True,
                should_notify=should_notify,
                check_logs=check_logs,
                previous_status=previous_status.value,
                new_status=DomainStatus.AVAILABLE.value
            )
        else:
            # Second check says unavailable
            logger.warning(
                f"⚠️ Domain {domain.domain} - conflicting results "
                f"(first: available, second: unavailable) → marking UNAVAILABLE"
            )

            domain.previous_status = previous_status
            domain.status = DomainStatus.UNAVAILABLE
            domain.last_checked = datetime.utcnow()

            await db.commit()

            return VerificationResult(
                is_available=False,
                should_notify=False,
                check_logs=check_logs,
                previous_status=previous_status.value,
                new_status=DomainStatus.UNAVAILABLE.value
            )

    async def save_check_logs(
        self,
        domain_id: int,
        check_logs: List[dict],
        db: AsyncSession
    ) -> None:
        """
        Save check logs to database

        Args:
            domain_id: Domain ID
            check_logs: List of check log dictionaries
            db: Database session
        """
        for log_data in check_logs:
            check_log = CheckLog(
                domain_id=domain_id,
                **log_data
            )
            db.add(check_log)

        await db.commit()
        logger.debug(f"Saved {len(check_logs)} check logs for domain_id={domain_id}")


# Global instance
availability_service = AvailabilityService()
