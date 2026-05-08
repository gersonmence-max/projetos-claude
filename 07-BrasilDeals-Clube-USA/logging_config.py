"""
Logging configuration for BrasilDeals
Configures JSON logging for all modules
"""
import logging
import logging.config
import os
import json
from pathlib import Path
from pythonjsonlogger import jsonlogger

from config import config


def setup_logging():
    """Configure logging with JSON format"""

    # Create logs directory if it doesn't exist
    log_dir = Path(config.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": "%(timestamp)s %(level)s %(name)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": config.LOG_LEVEL,
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": config.LOG_LEVEL,
                "formatter": "json",
                "filename": config.LOG_FILE,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf-8"
            }
        },
        "root": {
            "level": config.LOG_LEVEL,
            "handlers": ["console", "file"]
        },
        "loggers": {
            "config": {"level": config.LOG_LEVEL},
            "database": {"level": config.LOG_LEVEL},
            "scraper": {"level": config.LOG_LEVEL},
            "messenger": {"level": config.LOG_LEVEL},
            "scheduler": {"level": config.LOG_LEVEL},
            "dashboard": {"level": config.LOG_LEVEL},
        }
    }

    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    return logger


# Setup on import
logger = setup_logging()
