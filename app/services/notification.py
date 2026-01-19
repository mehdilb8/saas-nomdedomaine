"""
Notification Service - Send Discord webhook notifications
"""
import asyncio
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Domain, Notification


@dataclass
class NotificationResult:
    """Result of notification attempt"""
    success: bool
    http_status: Optional[int]
    response: Optional[str]
    error: Optional[str] = None


class NotificationService:
    """Service for sending Discord webhook notifications"""

    def __init__(self):
        self.webhook_url = settings.discord_webhook_url
        self.retry_count = settings.discord_retry_count
        self.retry_delay = settings.discord_retry_delay

    def build_discord_embed(self, domain: Domain) -> dict:
        """
        Build Discord embed message for available domain

        Args:
            domain: Domain model instance

        Returns:
            Discord webhook payload with embed
        """
        embed = {
            "embeds": [{
                "title": "🎯 Domaine disponible !",
                "color": 65280,  # Green (#00FF00)
                "fields": [
                    {
                        "name": "📍 Domaine",
                        "value": domain.domain,
                        "inline": True
                    },
                    {
                        "name": "🏷️ TLD",
                        "value": domain.tld,
                        "inline": True
                    },
                    {
                        "name": "🎨 Niche",
                        "value": domain.niche or "Non définie",
                        "inline": True
                    },
                    {
                        "name": "📊 Traffic",
                        "value": self._format_number(domain.traffic),
                        "inline": True
                    },
                    {
                        "name": "🔗 Referring Domains",
                        "value": self._format_number(domain.referring_domains),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Domain Monitor"
                },
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        return embed

    def _format_number(self, num: int) -> str:
        """
        Format number with thousands separator

        Args:
            num: Number to format

        Returns:
            Formatted string (e.g., "1,234")
        """
        if num == 0:
            return "0"
        return f"{num:,}"

    async def send_discord_notification(
        self,
        domain: Domain,
        db: AsyncSession
    ) -> NotificationResult:
        """
        Send Discord notification with retry logic

        Args:
            domain: Domain model instance
            db: Database session

        Returns:
            NotificationResult with success status

        Logic:
            1. Build embed message
            2. Try to send with httpx (max retry_count attempts)
            3. Handle rate limiting (429)
            4. Log result to database
        """
        logger.info(f"📨 Sending Discord notification for domain: {domain.domain}")

        # Build embed
        embed = self.build_discord_embed(domain)

        # Try sending with retries
        for attempt in range(1, self.retry_count + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.webhook_url,
                        json=embed,
                        timeout=10.0
                    )

                    # Success (Discord returns 204 No Content)
                    if response.status_code == 204:
                        logger.success(
                            f"✅ Discord notification sent successfully for {domain.domain}"
                        )

                        # Save to database
                        await self._save_notification(
                            domain_id=domain.id,
                            success=True,
                            http_status=204,
                            response="Success",
                            db=db
                        )

                        return NotificationResult(
                            success=True,
                            http_status=204,
                            response="Success"
                        )

                    # Rate limited (429)
                    elif response.status_code == 429:
                        retry_after = response.json().get("retry_after", self.retry_delay)
                        logger.warning(
                            f"⏳ Discord rate limit hit for {domain.domain}, "
                            f"waiting {retry_after}s (attempt {attempt}/{self.retry_count})"
                        )

                        if attempt < self.retry_count:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            # Max retries reached
                            await self._save_notification(
                                domain_id=domain.id,
                                success=False,
                                http_status=429,
                                response=response.text,
                                db=db
                            )
                            return NotificationResult(
                                success=False,
                                http_status=429,
                                response=response.text,
                                error="Rate limit exceeded"
                            )

                    # Other error status
                    else:
                        logger.error(
                            f"❌ Discord notification failed for {domain.domain}: "
                            f"HTTP {response.status_code} - {response.text}"
                        )

                        if attempt < self.retry_count:
                            await asyncio.sleep(self.retry_delay * attempt)
                            continue
                        else:
                            await self._save_notification(
                                domain_id=domain.id,
                                success=False,
                                http_status=response.status_code,
                                response=response.text,
                                db=db
                            )
                            return NotificationResult(
                                success=False,
                                http_status=response.status_code,
                                response=response.text,
                                error=f"HTTP {response.status_code}"
                            )

            except Exception as e:
                logger.error(
                    f"❌ Exception sending Discord notification for {domain.domain}: {str(e)}"
                )

                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                else:
                    await self._save_notification(
                        domain_id=domain.id,
                        success=False,
                        http_status=None,
                        response=str(e),
                        db=db
                    )
                    return NotificationResult(
                        success=False,
                        http_status=None,
                        response=None,
                        error=str(e)
                    )

        # Should never reach here
        return NotificationResult(
            success=False,
            http_status=None,
            response=None,
            error="Max retries exceeded"
        )

    async def _save_notification(
        self,
        domain_id: int,
        success: bool,
        http_status: Optional[int],
        response: str,
        db: AsyncSession
    ) -> None:
        """
        Save notification result to database

        Args:
            domain_id: Domain ID
            success: Whether notification was successful
            http_status: HTTP status code
            response: Response text
            db: Database session
        """
        notification = Notification(
            domain_id=domain_id,
            success=success,
            http_status=http_status,
            webhook_response=response
        )
        db.add(notification)
        await db.commit()

    async def send_domain_lost_notification(
        self,
        domain: Domain,
        db: AsyncSession
    ) -> NotificationResult:
        """
        Send Discord notification when a domain becomes unavailable

        Args:
            domain: Domain model instance
            db: Database session

        Returns:
            NotificationResult with success status
        """
        logger.info(f"⚠️ Sending 'domain lost' notification for: {domain.domain}")

        # Calculate time since it was available
        time_available = ""
        if domain.last_available:
            delta = datetime.utcnow() - domain.last_available
            hours = int(delta.total_seconds() / 3600)
            minutes = int((delta.total_seconds() % 3600) / 60)
            time_available = f"{hours}h {minutes}m"

        embed = {
            "embeds": [{
                "title": "⚠️ Domaine perdu !",
                "description": f"Le domaine **{domain.domain}** n'est plus disponible.",
                "color": 16711680,  # Red (#FF0000)
                "fields": [
                    {
                        "name": "📍 Domaine",
                        "value": domain.domain,
                        "inline": True
                    },
                    {
                        "name": "🏷️ TLD",
                        "value": domain.tld,
                        "inline": True
                    },
                    {
                        "name": "🎨 Niche",
                        "value": domain.niche or "Non définie",
                        "inline": True
                    },
                    {
                        "name": "⏱️ Temps disponible",
                        "value": time_available or "Inconnu",
                        "inline": True
                    },
                    {
                        "name": "📊 Traffic",
                        "value": self._format_number(domain.traffic),
                        "inline": True
                    },
                    {
                        "name": "🔗 Referring Domains",
                        "value": self._format_number(domain.referring_domains),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Domain Monitor - Watcher arrêté"
                },
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=embed,
                    timeout=10.0
                )

                if response.status_code == 204:
                    logger.success(f"✅ 'Domain lost' notification sent for {domain.domain}")

                    await self._save_notification(
                        domain_id=domain.id,
                        success=True,
                        http_status=204,
                        response="Success - Domain Lost",
                        db=db
                    )

                    return NotificationResult(
                        success=True,
                        http_status=204,
                        response="Success"
                    )
                else:
                    logger.error(f"❌ Failed to send 'domain lost' notification: HTTP {response.status_code}")
                    return NotificationResult(
                        success=False,
                        http_status=response.status_code,
                        response=response.text,
                        error=f"HTTP {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"❌ Exception sending 'domain lost' notification: {str(e)}")
            return NotificationResult(
                success=False,
                http_status=None,
                response=None,
                error=str(e)
            )

    async def send_test_notification(self) -> NotificationResult:
        """
        Send a test notification to verify webhook configuration

        Returns:
            NotificationResult with success status
        """
        logger.info("🧪 Sending test Discord notification")

        test_embed = {
            "embeds": [{
                "title": "🧪 Test Notification - Domain Monitor",
                "description": "This is a test notification to verify your Discord webhook is working correctly.",
                "color": 3447003,  # Blue
                "fields": [
                    {
                        "name": "Status",
                        "value": "✅ Webhook configured successfully",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Domain Monitor - Test"
                },
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=test_embed,
                    timeout=10.0
                )

                if response.status_code == 204:
                    logger.success("✅ Test notification sent successfully")
                    return NotificationResult(
                        success=True,
                        http_status=204,
                        response="Success"
                    )
                else:
                    logger.error(f"❌ Test notification failed: HTTP {response.status_code}")
                    return NotificationResult(
                        success=False,
                        http_status=response.status_code,
                        response=response.text,
                        error=f"HTTP {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"❌ Exception sending test notification: {str(e)}")
            return NotificationResult(
                success=False,
                http_status=None,
                response=None,
                error=str(e)
            )


# Global instance
notification_service = NotificationService()
