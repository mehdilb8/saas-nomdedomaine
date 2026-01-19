"""
Tests for Availability Service
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.models import Domain, DomainStatus
from app.services.availability import availability_service
from app.services.dns_checker import CheckResult


class TestAvailabilityService:
    """Test availability verification logic"""

    @pytest.mark.asyncio
    async def test_verify_domain_unavailable(self, test_db, sample_domain):
        """Test verification when domain is unavailable"""

        # Mock DNS checker to return unavailable
        with patch('app.services.availability.dns_checker.check_domain_availability') as mock_check:
            mock_check.return_value = CheckResult(
                available=False,
                method="dns_8_8_8_8",
                response_time_ms=50,
                error=None
            )

            result = await availability_service.verify_domain(sample_domain, test_db)

            assert result.is_available is False
            assert result.should_notify is False
            assert result.new_status == "unavailable"
            assert len(result.check_logs) == 1

    @pytest.mark.asyncio
    async def test_verify_domain_available_with_transition(self, test_db, sample_domain):
        """Test verification when domain becomes available (transition)"""

        # Set initial status to unavailable
        sample_domain.status = DomainStatus.UNAVAILABLE
        sample_domain.previous_status = DomainStatus.UNAVAILABLE
        await test_db.commit()

        # Mock DNS checker to return available for both checks
        with patch('app.services.availability.dns_checker.check_domain_availability') as mock_check:
            mock_check.return_value = CheckResult(
                available=True,
                method="dns_test",
                response_time_ms=50,
                error=None
            )

            result = await availability_service.verify_domain(sample_domain, test_db)

            assert result.is_available is True
            assert result.should_notify is True  # Transition detected
            assert result.new_status == "available"
            assert len(result.check_logs) == 2  # Two checks

    @pytest.mark.asyncio
    async def test_verify_domain_available_no_transition(self, test_db, sample_domain):
        """Test verification when domain stays available (no notification)"""

        # Set initial status to available
        sample_domain.status = DomainStatus.AVAILABLE
        sample_domain.previous_status = DomainStatus.AVAILABLE
        await test_db.commit()

        # Mock DNS checker to return available
        with patch('app.services.availability.dns_checker.check_domain_availability') as mock_check:
            mock_check.return_value = CheckResult(
                available=True,
                method="dns_test",
                response_time_ms=50,
                error=None
            )

            result = await availability_service.verify_domain(sample_domain, test_db)

            assert result.is_available is True
            assert result.should_notify is False  # No transition (anti-spam)
            assert result.new_status == "available"
