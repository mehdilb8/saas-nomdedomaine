"""
Tests for DNS Checker Service
"""
import pytest
from app.services.dns_checker import DNSChecker, dns_checker


class TestDNSChecker:
    """Test DNS checker functionality"""

    def test_extract_tld(self):
        """Test TLD extraction"""
        assert dns_checker.extract_tld("example.fr") == "fr"
        assert dns_checker.extract_tld("example.com") == "com"
        assert dns_checker.extract_tld("sub.example.net") == "net"
        assert dns_checker.extract_tld("invalid") == ""

    def test_is_supported_tld(self):
        """Test TLD support validation"""
        assert dns_checker.is_supported_tld("example.fr") is True
        assert dns_checker.is_supported_tld("example.com") is True
        assert dns_checker.is_supported_tld("example.net") is True
        assert dns_checker.is_supported_tld("example.org") is False
        assert dns_checker.is_supported_tld("example.io") is False

    @pytest.mark.asyncio
    async def test_check_existing_domain(self):
        """Test checking an existing domain (should be unavailable)"""
        result = await dns_checker.check_domain_availability(
            "google.com",
            "8.8.8.8"
        )

        assert result.available is False
        assert result.response_time_ms > 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_check_nonexistent_domain(self):
        """Test checking a non-existent domain (should be available)"""
        result = await dns_checker.check_domain_availability(
            "this-domain-definitely-does-not-exist-12345.com",
            "8.8.8.8"
        )

        assert result.available is True
        assert result.response_time_ms > 0
