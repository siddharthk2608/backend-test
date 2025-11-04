# logging_config.py
"""
Comprehensive Logging Configuration for Tax Planning Services
"""

import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
import sys
from datetime import datetime


def setup_logger(
    service_name: str = "app",
    log_dir: str = None,
    log_level: str = "INFO",
    max_bytes: int = 10485760,
    backup_count: int = 5,
    enable_console: bool = True,
    enable_debug_log: bool = True
):
    """Setup comprehensive logging for the service"""
    
    if log_dir is None:
        current_dir = Path(__file__).parent
        log_dir = current_dir.parent.parent / "logs" / service_name
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    app_log = log_dir / "app.log"
    error_log = log_dir / "error.log"
    debug_log = log_dir / "debug.log"
    
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False
    
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    app_handler = RotatingFileHandler(
        app_log,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)
    logger.addHandler(app_handler)
    
    error_handler = RotatingFileHandler(
        error_log,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    if enable_debug_log:
        debug_handler = TimedRotatingFileHandler(
            debug_log,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(detailed_formatter)
        logger.addHandler(debug_handler)
    
    logger.info("=" * 80)
    logger.info(f"{service_name.upper()} SERVICE LOGGING INITIALIZED")
    logger.info(f"Log Directory: {log_dir.absolute()}")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Console Output: {enable_console}")
    logger.info(f"Debug Logs: {enable_debug_log}")
    logger.info("=" * 80)
    
    return logger


def get_logger(name: str = None):
    """Get a logger instance"""
    return logging.getLogger(name) if name else logging.getLogger()
