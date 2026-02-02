"""Tests for ImageProcessor."""

import pytest
from pathlib import Path
from src.core.image_processor import ImageProcessor


class TestImageProcessor:
    """Test cases for ImageProcessor."""
    
    def test_init(self):
        """Test ImageProcessor initialization."""
        processor = ImageProcessor()
        assert processor is not None
        assert processor.logger is not None
    
    def test_detect_image_type_by_extension(self, tmp_path):
        """Test image type detection by extension."""
        processor = ImageProcessor()
        
        # Create dummy image file
        test_image = tmp_path / "test.img"
        test_image.write_bytes(b"dummy data")
        
        image_type = processor.detect_image_type(test_image)
        assert image_type == "img"
    
    def test_is_raw(self, tmp_path):
        """Test RAW format detection."""
        processor = ImageProcessor()
        
        # Test RAW file
        raw_file = tmp_path / "test.raw"
        raw_file.write_bytes(b"dummy data")
        assert processor.is_raw(raw_file) is True
        
        # Test non-RAW file
        img_file = tmp_path / "test.vmdk"
        img_file.write_bytes(b"dummy data")
        assert processor.is_raw(img_file) is False



