"""
api/main.py — FastAPI application entry point.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from narrative_harm_classifier.core.config import get_settings
from narrative_harm_classifier.api.routes import classify, validate, health, tracking, benchmark

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Taxonomy: {settings.taxonomy_config_path} v{settings.taxonomy_version}")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Narrative Harm Classification API\n\n"
            "Implements the D2.4a classification specification with multi-dimensional "
            "rule-based logic across targets, identities, harm mechanisms, and "
            "decision thresholds. Azure Text Analytics integrated for optional NLP signal "
            "amplification. Also provides escalation-chain tracking across sources over time "
            "and a templated benchmark suite for credible precision/recall reporting."
        ),
        lifespan=lifespan,
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(classify.router, prefix="/classify", tags=["Classification"])
    app.include_router(validate.router, prefix="/validate", tags=["Validation"])
    app.include_router(tracking.router, prefix="/tracking", tags=["Escalation Tracking"])
    app.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmark"])

    return app


app = create_app()
