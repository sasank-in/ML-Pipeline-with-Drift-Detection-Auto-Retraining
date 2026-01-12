"""Centralized logging for all services"""
import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logger(service_name: str, log_dir: str = "logs") -> logging.Logger:
    """Setup logger for a service"""
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)
    
    # Create logs directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # File handler
    log_file = f"{log_dir}/{service_name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger
