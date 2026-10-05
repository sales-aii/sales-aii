# -*- coding: utf-8 -*-
"""
Logging system for Sales.aii
"""

import sys
from loguru import logger as _loguru_logger
from config.config import settings


def setup_logger():
    """Configure and setup logger"""
    logger = _loguru_logger
    # Remove default logger
    logger.remove()
    
    # Console logger - handle None stdout in EXE
    try:
        sink = sys.stdout if sys.stdout is not None else str(settings.LOGS_DIR / 'stdout.log')
        logger.add(
            sink,
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level=settings.LOG_LEVEL
        )
    except Exception:
        try:
            logger.add(str(settings.LOGS_DIR / 'app.log'), level=settings.LOG_LEVEL)
        except Exception:
            logger.add(lambda msg: None)  # No-op sink
    
    # File logger
    log_file_path = str(settings.LOGS_DIR / settings.LOG_FILE)
    logger.add(
        log_file_path,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level=settings.LOG_LEVEL
    )
    
    return logger


# Initialize logger
logger = setup_logger()
