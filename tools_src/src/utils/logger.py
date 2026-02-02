"""Logging utility module for forensic image triage toolkit."""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


class ForensicLogger:
    """
    Centralized logging utility for the forensic toolkit.
    
    Provides file and console logging with configurable levels.
    """
    
    def __init__(self, name: str, log_dir: str = "logs", log_level: int = logging.INFO):
        """
        Initialize the logger.
        
        Args:
            name: Logger name (typically module name)
            log_dir: Directory for log files
            log_level: Logging level (default: INFO)
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configure file and console handlers."""
        # File handler
        log_file = self.log_dir / "forensic.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log critical message."""
        self.logger.critical(message)
    
    def exception(self, message: str):
        """Log exception with traceback."""
        self.logger.exception(message)


def get_logger(name: str, log_dir: str = "logs") -> ForensicLogger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
        log_dir: Log directory path
        
    Returns:
        ForensicLogger instance
    """
    return ForensicLogger(name, log_dir)



