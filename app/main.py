"""
Domain Monitor - FastAPI Main Application
"""
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import init_db, close_db
from app.routers import domains
from app.services.scheduler import scheduler_service
from app.services.watcher import watcher_service


# ============================================
# CONFIGURE LOGURU
# ============================================

def configure_logging():
    """Configure Loguru logging with file rotation and console output"""

    # Remove default handler
    logger.remove()

    # Console handler (colored output)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )

    # File handler (with rotation)
    logger.add(
        f"{settings.log_path}/app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        enqueue=True  # Thread-safe
    )

    # Error file handler (errors only)
    logger.add(
        f"{settings.log_path}/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        enqueue=True
    )

    logger.info("✅ Logging configured successfully")


# ============================================
# LIFESPAN CONTEXT MANAGER
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events

    Startup:
        - Configure logging
        - Initialize database
        - Start scheduler

    Shutdown:
        - Stop scheduler
        - Close database connections
    """
    # ========== STARTUP ==========
    logger.info("=" * 80)
    logger.info("🚀 Starting Domain Monitor Application")
    logger.info("=" * 80)

    # Configure logging
    configure_logging()

    # Log configuration
    logger.info(f"📋 Configuration:")
    logger.info(f"   - Environment: {settings.app_env}")
    logger.info(f"   - Debug: {settings.app_debug}")
    logger.info(f"   - Host: {settings.app_host}:{settings.app_port}")
    logger.info(f"   - Database: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
    logger.info(f"   - Check interval: {settings.check_interval_hours} hour(s)")
    logger.info(f"   - Supported TLDs: {', '.join(settings.supported_tlds_list)}")

    # Initialize database
    try:
        logger.info("🔌 Initializing database connection...")
        await init_db()
        logger.success("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        raise

    # Start scheduler
    try:
        logger.info("⏰ Starting scheduler...")
        scheduler_service.start_scheduler()
        logger.success("✅ Scheduler started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {str(e)}")
        raise

    logger.info("=" * 80)
    logger.success("✅ Application started successfully")
    logger.info("=" * 80)

    yield

    # ========== SHUTDOWN ==========
    logger.info("=" * 80)
    logger.info("🛑 Shutting down Domain Monitor Application")
    logger.info("=" * 80)

    # Stop all watchers
    try:
        logger.info("👁️ Stopping all watchers...")
        await watcher_service.stop_all_watchers()
        logger.success("✅ All watchers stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error stopping watchers: {str(e)}")

    # Stop scheduler
    try:
        logger.info("⏰ Stopping scheduler...")
        scheduler_service.shutdown_scheduler()
        logger.success("✅ Scheduler stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error stopping scheduler: {str(e)}")

    # Close database
    try:
        logger.info("🔌 Closing database connections...")
        await close_db()
        logger.success("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {str(e)}")

    logger.info("=" * 80)
    logger.success("✅ Application shutdown complete")
    logger.info("=" * 80)


# ============================================
# CREATE FASTAPI APPLICATION
# ============================================

app = FastAPI(
    title="Domain Monitor API",
    description="API for monitoring expired domain availability with Discord notifications",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================
# CORS MIDDLEWARE (Optional)
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# INCLUDE ROUTERS
# ============================================

app.include_router(domains.router)


# ============================================
# ROOT ENDPOINT
# ============================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Domain Monitor API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
        "stats": "/api/stats"
    }


# ============================================
# MAIN ENTRY POINT (for development)
# ============================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )
