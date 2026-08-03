import logging
import sys
from pathlib import Path
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """配置应用日志系统"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 创建日志目录
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

    # 配置日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # 文件处理器（可选）
    handlers = [console_handler]
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # 配置根日志器
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )

    # 降低第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成，级别: {settings.LOG_LEVEL}")

    return logger
