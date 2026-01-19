"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    app_name: str = "domain-monitor"
    app_env: str = "production"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 3010

    # Database MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_database: str = "domain_monitor"
    mysql_user: str = "domain_user"
    mysql_password: str
    mysql_root_password: str
    database_url: str

    # phpMyAdmin
    pma_host: str = "mysql"
    pma_port: int = 3306

    # Logging
    log_level: str = "INFO"
    log_path: str = "./logs"
    log_rotation: str = "10 MB"
    log_retention: str = "30 days"

    # Discord
    discord_webhook_url: str
    discord_retry_count: int = 3
    discord_retry_delay: int = 2

    # Scheduler
    check_interval_hours: int = 2
    batch_size: int = 50
    delay_between_checks_ms: int = 100
    double_check_delay_seconds: int = 5

    # DNS
    dns_timeout_seconds: int = 5
    dns_retry_count: int = 2
    dns_primary_server: str = "8.8.8.8"
    dns_secondary_server: str = "1.1.1.1"

    # Supported TLDs
    supported_tlds: str = "fr,com,net"

    @property
    def supported_tlds_list(self) -> List[str]:
        """Return supported TLDs as a list"""
        return [tld.strip() for tld in self.supported_tlds.split(",")]


# Global settings instance
settings = Settings()
