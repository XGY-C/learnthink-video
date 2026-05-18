import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON 格式化器，适用于生产环境的日志聚合系统。"""
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def configure_logging(level: str = "INFO", log_to_file: bool = False, use_json: bool = False) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # 定义格式
    if use_json:
        formatter = JSONFormatter()
    else:
        log_format = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        formatter = logging.Formatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 清理旧 handlers 避免重复
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件 Handler (可选)
    if log_to_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 保持 app.* 命名空间的整洁
    app_logger = logging.getLogger("app")
    app_logger.setLevel(numeric_level)
    app_logger.propagate = True
