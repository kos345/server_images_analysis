"""Tests for ForensicLogger."""

import pytest
from pathlib import Path
from src.utils.logger import ForensicLogger, get_logger


class TestForensicLogger:
    """Test cases for ForensicLogger."""
    
    def test_init(self, tmp_path):
        """Test logger initialization."""
        logger = ForensicLogger("test_logger", str(tmp_path))
        assert logger is not None
        assert logger.name == "test_logger"
    
    def test_get_logger(self, tmp_path):
        """Test get_logger function."""
        logger = get_logger("test", str(tmp_path))
        assert logger is not None
    
    def test_logging_methods(self, tmp_path):
        """Test logging methods."""
        logger = ForensicLogger("test_logger", str(tmp_path))
        
        # These should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")



