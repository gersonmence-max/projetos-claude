import logging
import os
from pythonjsonlogger import jsonlogger
from logging.handlers import TimedRotatingFileHandler

from config import LOG_FILE_PATH, LOG_LEVEL

def setup_logging():
    """Configure JSON logging for file and console, with daily rotation."""
    log_file_path = LOG_FILE_PATH
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate logs if called multiple times
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # JSON formatter
    formatter = jsonlogger.JsonFormatter(
        '%(levelname)s %(asctime)s %(name)s %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",
        interval=1,
        backupCount=7, # Keep 7 days of logs
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING) # Reduce noise from http clients
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    root_logger.info(f"Logging configured. Level: {LOG_LEVEL}, File: {LOG_FILE_PATH}")

setup_logging()
logger = logging.getLogger(__name__)