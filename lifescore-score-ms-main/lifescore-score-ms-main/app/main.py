"""
Main application entry point.

This module initializes the FastAPI app and includes the API routes.
"""

# pylint: disable=wrong-import-position
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from sqlalchemy.sql import text as sqlalchemy_text
import sentry_sdk
from app.shared_db.config import settings  # noqa: E402
from app.shared_db.core.logging_config import get_logger

logger = get_logger(__name__)

try:
    sentry_sdk.init(
        dsn=settings.SENTRY_SCORING_DSN,
        traces_sample_rate=1.0,
        environment=settings.ENV,
        attach_stacktrace=True,
    )
except Exception as e:
    logger.error("Failed to initialize Sentry: %s", str(e))


APP_DIR = str(Path(__file__).resolve().parent)
SHARED_DB_PATH = str(Path(APP_DIR) / "shared_db")

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

try:
    from app.shared_db.middlewares.trailing_slash import RemoveTrailingSlashMiddleware
    from app.shared_db.core.redis_client import redis_client

    from app.shared_db.database import (
        async_engine,
        initialize_db,
    )  # noqa: E402

    logger.info("Successfully imported settings from shared_db.config")
except ImportError as e:
    logger.error("Failed to import settings: %s", str(e))
    if os.path.exists(SHARED_DB_PATH):
        logger.info("shared_db path exists: %s", SHARED_DB_PATH)
    else:
        logger.error("shared_db path does not exist: %s", SHARED_DB_PATH)

# flake8: noqa: E402
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.endpoints import scoring
from .metadata import openapi_tags, APP_DESCRIPTION


@asynccontextmanager
async def get_lifespan(app: FastAPI):  # pylint: disable=unused-argument, disable=W0621
    """
    Lifespan context manager for FastAPI application lifecycle management.

    This context manager handles the application's startup and shutdown sequences,
    ensuring proper initialization and cleanup of resources. It's particularly
    focused on Redis connection management but can be extended for other resources.

    Args:
        app (FastAPI): The FastAPI application instance. Required by FastAPI's
                      lifespan protocol but not used directly in this function.

    Yields:
        None: Control is yielded to FastAPI during the application's runtime.

    Raises:
        Exception: Any unhandled exceptions during startup or shutdown will be
                  logged and re-raised, potentially terminating the application.

    Lifecycle Phases:
        Startup:
            1. Attempts to establish Redis connection
            2. Verifies connection with ping
            3. Logs successful connection

        Runtime:
            - Yields control to FastAPI
            - Application serves requests
            - Resources remain active

        Shutdown:
            1. Gracefully closes Redis connection
            2. Logs shutdown status
            3. Ensures cleanup of resources

    Example:
        ```python
        app = FastAPI(lifespan=get_lifespan)
        # The lifespan context manager handles startup/shutdown automatically
        ```

    Note:
        This function is critical for proper resource management and should be
        modified carefully. Any additional resource initialization/cleanup should
        be added here in the appropriate phase.
    """

    try:
        await redis_client.connect()
        logger.info("Redis connection established successfully")

        # Initialize database and get session maker
        session_maker = await initialize_db()
        if session_maker is None:
            raise RuntimeError("Failed to initialize database session maker")

        # Test database connection
        async with session_maker() as session:
            await session.execute(sqlalchemy_text("SELECT 1"))
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error("Failed to initialize connections: %s", str(e))
        raise

    yield

    try:
        await redis_client.close()
        if async_engine is not None:
            await async_engine.dispose()
        logger.info("Connections closed successfully")
    except Exception as e:
        logger.error("Error during cleanup: %s", str(e))
        raise


app = FastAPI(
    title="LifeScore API",
    description=APP_DESCRIPTION,
    version="1.0.0",
    terms_of_service="https://getlifescore.com/terms-and-conditions",
    contact={
        "name": "LifeScore API Support",
        "url": "https://getlifescore.com/contact",
        "email": "support@Lifescore.health",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://getlifescore.com/",
    },
    openapi_tags=openapi_tags,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    lifespan=get_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(RemoveTrailingSlashMiddleware)

logger.info("App initialized with middleware configuration")

logger.info("App initialized")

try:
    logger.info("Including API routes")
    app.include_router(scoring.router, prefix="/scoring", tags=["Scoring"])
    app.include_router(scoring.protected_router, prefix="/scoring", tags=["Scoring"])
    logger.info("API routes included successfully")
except Exception as e:
    logger.error("Error including API routes: %s", str(e))
    raise

logger.info("App initialization completed")

logger.info("Environment: %s", settings.ENV)
