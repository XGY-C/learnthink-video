import logging


def configure_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    log_format = "%(asctime)s %(levelname)s %(name)s - %(message)s"

    # Keep root logger sane for libraries while avoiding reliance on basicConfig no-op behavior.
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    if not root_logger.handlers:
        logging.basicConfig(level=numeric_level, format=log_format)
    else:
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)

    # Let app.* bubble up to uvicorn/root handlers; avoids stale dedicated handlers under reload.
    app_logger = logging.getLogger("app")
    app_logger.setLevel(numeric_level)
    app_logger.propagate = True
    if app_logger.handlers:
        app_logger.handlers.clear()
