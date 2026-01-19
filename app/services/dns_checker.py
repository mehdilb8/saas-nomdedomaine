"""
DNS Checker Service - Verify domain availability using DNS queries
"""
import time
from dataclasses import dataclass
from typing import Optional
import dns.resolver
import dns.exception
from loguru import logger
from app.config import settings


@dataclass
class CheckResult:
    """Result of a DNS availability check"""
    available: bool
    method: str
    response_time_ms: int
    error: Optional[str] = None


class DNSChecker:
    """Service for checking domain availability via DNS"""

    def __init__(self):
        self.timeout = settings.dns_timeout_seconds
        self.retry_count = settings.dns_retry_count
        self.primary_server = settings.dns_primary_server
        self.secondary_server = settings.dns_secondary_server

    async def check_domain_availability(
        self,
        domain: str,
        dns_server: str
    ) -> CheckResult:
        """
        Check if a domain is available using DNS resolution

        Args:
            domain: Full domain name (e.g., example.fr)
            dns_server: DNS server IP to use (e.g., 8.8.8.8)

        Returns:
            CheckResult with availability status and metadata

        Logic:
            - If domain resolves to IP(s) → unavailable
            - If NXDOMAIN → available
            - If SERVFAIL/Timeout after retries → likely available
            - Other errors → unknown (error logged)
        """
        method = f"dns_{dns_server.replace('.', '_')}"

        # Create DNS resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout

        for attempt in range(1, self.retry_count + 1):
            try:
                # Start timer
                start_time = time.time()

                # Try to resolve domain (A record)
                answer = resolver.resolve(domain, 'A')

                # Calculate response time
                response_time_ms = int((time.time() - start_time) * 1000)

                # If we get a response with IPs, domain is NOT available
                if answer:
                    logger.debug(
                        f"Domain {domain} is UNAVAILABLE (resolved to IPs) "
                        f"via {dns_server} in {response_time_ms}ms"
                    )
                    return CheckResult(
                        available=False,
                        method=method,
                        response_time_ms=response_time_ms,
                        error=None
                    )

            except dns.resolver.NXDOMAIN:
                # NXDOMAIN = domain does not exist = AVAILABLE
                response_time_ms = int((time.time() - start_time) * 1000)
                logger.debug(
                    f"Domain {domain} is AVAILABLE (NXDOMAIN) "
                    f"via {dns_server} in {response_time_ms}ms"
                )
                return CheckResult(
                    available=True,
                    method=method,
                    response_time_ms=response_time_ms,
                    error=None
                )

            except (dns.resolver.Timeout, dns.resolver.NoNameservers, dns.exception.DNSException) as e:
                error_type = type(e).__name__

                if attempt < self.retry_count:
                    logger.warning(
                        f"DNS check for {domain} via {dns_server} failed "
                        f"(attempt {attempt}/{self.retry_count}): {error_type}"
                    )
                    time.sleep(0.5)  # Small delay before retry
                    continue
                else:
                    # After all retries, consider it likely available
                    response_time_ms = int((time.time() - start_time) * 1000)
                    logger.warning(
                        f"Domain {domain} likely AVAILABLE after {self.retry_count} retries "
                        f"(timeout/servfail) via {dns_server}"
                    )
                    return CheckResult(
                        available=True,
                        method=method,
                        response_time_ms=response_time_ms,
                        error=f"{error_type} after {self.retry_count} retries"
                    )

            except Exception as e:
                # Unexpected error
                response_time_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"Unexpected error checking {domain} via {dns_server}: {str(e)}"
                )
                return CheckResult(
                    available=False,  # Unknown, mark as unavailable to be safe
                    method=method,
                    response_time_ms=response_time_ms,
                    error=str(e)
                )

        # Should never reach here, but just in case
        return CheckResult(
            available=False,
            method=method,
            response_time_ms=0,
            error="Unexpected flow"
        )

    def extract_tld(self, domain: str) -> str:
        """
        Extract TLD from domain name

        Args:
            domain: Full domain name (e.g., example.fr)

        Returns:
            TLD without dot (e.g., 'fr')
        """
        parts = domain.split('.')
        if len(parts) >= 2:
            return parts[-1].lower()
        return ""

    def is_supported_tld(self, domain: str) -> bool:
        """
        Check if domain TLD is supported

        Args:
            domain: Full domain name

        Returns:
            True if TLD is in supported list
        """
        tld = self.extract_tld(domain)
        return tld in settings.supported_tlds_list

    def get_dns_server_for_tld(self, tld: str) -> str:
        """
        Get the appropriate DNS server for a TLD

        Args:
            tld: Top-level domain (e.g., 'fr', 'com', 'net')

        Returns:
            DNS server IP address

        DNS Servers by TLD:
            .fr  → AFNIC (192.134.4.1)
            .com → Verisign (199.7.91.13)
            .net → Verisign (199.7.91.13)
            other → Google DNS (8.8.8.8)
        """
        tld = tld.lower()

        # AFNIC DNS for .fr domains
        if tld == "fr":
            return "192.134.4.1"  # dns.nic.fr

        # Verisign DNS for .com and .net
        elif tld in ["com", "net"]:
            return "199.7.91.13"  # a.gtld-servers.net

        # Fallback to Google DNS
        else:
            return "8.8.8.8"


# Global instance
dns_checker = DNSChecker()
