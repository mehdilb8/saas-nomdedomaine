"""
Seed script to populate database with test data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Domain, DomainStatus
from loguru import logger


async def seed_database():
    """Seed database with sample domains"""

    logger.info("🌱 Starting database seeding...")

    sample_domains = [
        {
            "domain": "tech-startup.fr",
            "tld": "fr",
            "niche": "Tech",
            "traffic": 5000,
            "referring_domains": 150,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "finance-blog.com",
            "tld": "com",
            "niche": "Finance",
            "traffic": 10000,
            "referring_domains": 300,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "health-tips.net",
            "tld": "net",
            "niche": "Health",
            "traffic": 3000,
            "referring_domains": 80,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "travel-guide.fr",
            "tld": "fr",
            "niche": "Travel",
            "traffic": 7500,
            "referring_domains": 200,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "food-recipes.com",
            "tld": "com",
            "niche": "Food",
            "traffic": 12000,
            "referring_domains": 400,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "gaming-news.net",
            "tld": "net",
            "niche": "Gaming",
            "traffic": 15000,
            "referring_domains": 500,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "fashion-trends.fr",
            "tld": "fr",
            "niche": "Fashion",
            "traffic": 8000,
            "referring_domains": 250,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "sports-analytics.com",
            "tld": "com",
            "niche": "Sports",
            "traffic": 6000,
            "referring_domains": 180,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "education-platform.net",
            "tld": "net",
            "niche": "Education",
            "traffic": 9000,
            "referring_domains": 320,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        },
        {
            "domain": "real-estate-market.fr",
            "tld": "fr",
            "niche": "Real Estate",
            "traffic": 11000,
            "referring_domains": 350,
            "status": DomainStatus.UNKNOWN,
            "is_active": True
        }
    ]

    async with AsyncSessionLocal() as db:
        try:
            # Add domains
            for domain_data in sample_domains:
                domain = Domain(**domain_data)
                db.add(domain)
                logger.info(f"✅ Added domain: {domain_data['domain']}")

            await db.commit()

            logger.success(f"🎉 Successfully seeded {len(sample_domains)} domains!")

        except Exception as e:
            logger.error(f"❌ Error seeding database: {str(e)}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
