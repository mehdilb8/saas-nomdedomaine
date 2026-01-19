"""
Watcher Service - Continuous monitoring for available domains
"""
import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Domain, DomainStatus
from app.database import AsyncSessionLocal
from app.services.dns_checker import dns_checker
from app.services.notification import notification_service


class DomainWatcher:
    """Watcher for a single domain - checks every 2 seconds"""

    def __init__(self, domain_id: int, domain_name: str):
        self.domain_id = domain_id
        self.domain_name = domain_name
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start watching the domain"""
        if self.is_running:
            logger.warning(f"Watcher for {self.domain_name} is already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._watch_loop())
        logger.success(f"🔍 Started watcher for {self.domain_name} (checking every 2 seconds)")

    async def stop(self):
        """Stop watching the domain"""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info(f"🛑 Stopped watcher for {self.domain_name}")

    async def _watch_loop(self):
        """Main watch loop - checks every 2 seconds"""
        logger.info(f"👁️ Watching {self.domain_name} - checking every 2 seconds")

        while self.is_running:
            try:
                async with AsyncSessionLocal() as db:
                    # Get domain from database
                    from sqlalchemy import select
                    result = await db.execute(
                        select(Domain).where(Domain.id == self.domain_id)
                    )
                    domain = result.scalar_one_or_none()

                    if not domain:
                        logger.error(f"Domain {self.domain_name} not found, stopping watcher")
                        await self.stop()
                        break

                    # Check availability
                    check_result = await dns_checker.check_domain_availability(
                        domain.domain,
                        dns_checker.get_dns_server_for_tld(domain.tld)
                    )

                    # If domain is still AVAILABLE
                    if check_result.available:
                        logger.debug(f"✅ {self.domain_name} is still AVAILABLE")
                        # Keep status as available, no notification (anti-spam)
                        domain.last_checked = datetime.utcnow()
                        await db.commit()

                    # If domain became UNAVAILABLE
                    else:
                        logger.warning(f"⚠️ {self.domain_name} became UNAVAILABLE - stopping watcher")

                        # Update domain status
                        domain.previous_status = domain.status
                        domain.status = DomainStatus.UNAVAILABLE
                        domain.is_active = False  # Stop monitoring
                        domain.last_checked = datetime.utcnow()
                        await db.commit()

                        # Send notification that domain was lost
                        try:
                            await notification_service.send_domain_lost_notification(
                                domain, db
                            )
                        except Exception as e:
                            logger.error(f"Failed to send lost notification: {str(e)}")

                        # Stop watcher
                        await self.stop()
                        break

                # Wait 2 seconds before next check
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                logger.info(f"Watcher for {self.domain_name} was cancelled")
                break
            except Exception as e:
                logger.error(f"Error in watcher for {self.domain_name}: {str(e)}")
                await asyncio.sleep(2)  # Continue even on error


class WatcherService:
    """Service to manage multiple domain watchers"""

    def __init__(self):
        self.watchers: Dict[int, DomainWatcher] = {}

    async def start_watcher(self, domain_id: int, domain_name: str):
        """Start a watcher for a domain"""
        # Stop existing watcher if any
        if domain_id in self.watchers:
            await self.stop_watcher(domain_id)

        # Create and start new watcher
        watcher = DomainWatcher(domain_id, domain_name)
        self.watchers[domain_id] = watcher
        await watcher.start()

        logger.success(f"🚀 Watcher started for domain {domain_name} (ID: {domain_id})")

    async def stop_watcher(self, domain_id: int):
        """Stop a watcher for a domain"""
        if domain_id not in self.watchers:
            return

        watcher = self.watchers[domain_id]
        await watcher.stop()
        del self.watchers[domain_id]

        logger.info(f"🛑 Watcher stopped for domain ID {domain_id}")

    async def stop_all_watchers(self):
        """Stop all active watchers"""
        logger.info(f"🛑 Stopping all {len(self.watchers)} active watchers...")

        for domain_id in list(self.watchers.keys()):
            await self.stop_watcher(domain_id)

        logger.success("✅ All watchers stopped")

    def get_active_watchers_count(self) -> int:
        """Get number of active watchers"""
        return len(self.watchers)

    def is_watching(self, domain_id: int) -> bool:
        """Check if a domain is being watched"""
        return domain_id in self.watchers


# Global instance
watcher_service = WatcherService()
