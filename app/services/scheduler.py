"""
Scheduler Service - Automated domain checking with APScheduler
"""
import asyncio
from datetime import datetime
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Domain, DomainStatus
from app.services.availability import availability_service
from app.services.notification import notification_service


class SchedulerService:
    """Service for scheduling automated domain checks"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Europe/Paris")
        self.check_interval_hours = settings.check_interval_hours
        self.batch_size = settings.batch_size
        self.delay_between_checks_ms = settings.delay_between_checks_ms
        self.is_running = False

    async def run_check_cycle(self) -> None:
        """
        Main check cycle - verify all active domains

        Logic:
            1. Get all active domains
            2. Process in batches
            3. For each domain:
               - Verify availability
               - Send notification if needed
               - Save check logs
            4. Log summary statistics
            5. Call cleanup procedure
        """
        start_time = datetime.utcnow()
        logger.info("=" * 80)
        logger.info("🚀 Starting domain check cycle")
        logger.info("=" * 80)

        # Counters
        total = 0
        checked = 0
        available_count = 0
        notifications_sent = 0
        errors = 0

        async with AsyncSessionLocal() as db:
            try:
                # Get all active domains
                stmt = select(Domain).where(Domain.is_active == True)
                result = await db.execute(stmt)
                domains = result.scalars().all()

                total = len(domains)
                logger.info(f"📊 Found {total} active domains to check")

                if total == 0:
                    logger.warning("⚠️ No active domains found, skipping cycle")
                    return

                # Process in batches
                for i in range(0, total, self.batch_size):
                    batch = domains[i:i + self.batch_size]
                    batch_num = (i // self.batch_size) + 1
                    total_batches = (total + self.batch_size - 1) // self.batch_size

                    logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} domains)")

                    for domain in batch:
                        try:
                            # Verify domain
                            logger.debug(f"Checking domain: {domain.domain}")
                            verification_result = await availability_service.verify_domain(
                                domain=domain,
                                db=db
                            )

                            checked += 1

                            # Save check logs
                            await availability_service.save_check_logs(
                                domain_id=domain.id,
                                check_logs=verification_result.check_logs,
                                db=db
                            )

                            # Count available domains
                            if verification_result.is_available:
                                available_count += 1

                                # Send notification if needed
                                if verification_result.should_notify:
                                    logger.info(f"📨 Sending notification for {domain.domain}")
                                    notif_result = await notification_service.send_discord_notification(
                                        domain=domain,
                                        db=db
                                    )

                                    if notif_result.success:
                                        notifications_sent += 1

                                        # Update check logs to mark notification sent
                                        await db.execute(
                                            text(
                                                "UPDATE check_logs SET notification_sent = TRUE "
                                                "WHERE domain_id = :domain_id "
                                                "ORDER BY checked_at DESC LIMIT 1"
                                            ),
                                            {"domain_id": domain.id}
                                        )
                                        await db.commit()

                            # Small delay between checks to avoid overwhelming DNS servers
                            await asyncio.sleep(self.delay_between_checks_ms / 1000.0)

                        except Exception as e:
                            errors += 1
                            logger.error(f"❌ Error checking domain {domain.domain}: {str(e)}")
                            continue

                # Calculate duration
                duration = (datetime.utcnow() - start_time).total_seconds()

                # Log summary
                logger.info("=" * 80)
                logger.success(f"✅ Check cycle completed in {duration:.2f}s")
                logger.info(f"📊 Statistics:")
                logger.info(f"   - Total domains: {total}")
                logger.info(f"   - Checked: {checked}")
                logger.info(f"   - Available: {available_count}")
                logger.info(f"   - Notifications sent: {notifications_sent}")
                logger.info(f"   - Errors: {errors}")
                logger.info("=" * 80)

                # Call cleanup procedure (remove old logs)
                await self._cleanup_old_logs(db)

            except Exception as e:
                logger.error(f"❌ Fatal error in check cycle: {str(e)}")
                raise

    async def _cleanup_old_logs(self, db: AsyncSession) -> None:
        """
        Call MySQL stored procedure to cleanup old logs

        Args:
            db: Database session
        """
        try:
            logger.debug("🧹 Running cleanup_old_logs procedure")
            await db.execute(text("CALL cleanup_old_logs()"))
            await db.commit()
            logger.debug("✅ Cleanup procedure completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup procedure failed: {str(e)}")

    def start_scheduler(self) -> None:
        """
        Start the APScheduler

        Adds the check cycle job and starts the scheduler
        """
        if self.is_running:
            logger.warning("⚠️ Scheduler is already running")
            return

        logger.info("🚀 Starting scheduler")

        # Add job
        self.scheduler.add_job(
            self.run_check_cycle,
            trigger=IntervalTrigger(hours=self.check_interval_hours),
            id="domain_check_cycle",
            name="Domain Availability Check Cycle",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent executions
            coalesce=True,    # Merge missed executions
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        # Log next run time
        next_run = self.scheduler.get_job("domain_check_cycle").next_run_time
        logger.success(f"✅ Scheduler started successfully")
        logger.info(f"⏰ Next check cycle: {next_run}")
        logger.info(f"🔄 Check interval: every {self.check_interval_hours} hour(s)")

    def shutdown_scheduler(self) -> None:
        """
        Shutdown the APScheduler gracefully
        """
        if not self.is_running:
            logger.warning("⚠️ Scheduler is not running")
            return

        logger.info("🛑 Shutting down scheduler")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.success("✅ Scheduler stopped successfully")

    def get_next_run_time(self) -> datetime:
        """
        Get the next scheduled run time

        Returns:
            Next run datetime or None if not scheduled
        """
        if not self.is_running:
            return None

        job = self.scheduler.get_job("domain_check_cycle")
        if job:
            return job.next_run_time
        return None


# Global instance
scheduler_service = SchedulerService()
