import logging
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(
    level=settings.log_level,
    log_to_file=settings.log_to_file,
    use_json=settings.use_json_log,
)
logger = logging.getLogger("app.main")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "[startup] service=%s env=%s log_level=%s configured_port=%s",
        settings.app_name,
        settings.app_env,
        settings.log_level,
        settings.port,
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("[shutdown] service=%s", settings.app_name)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
