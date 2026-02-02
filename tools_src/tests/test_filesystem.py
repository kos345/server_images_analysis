"""Tests for FileSystemUtils."""

import pytest
from pathlib import Path
from src.utils.filesystem import FileSystemUtils


class TestFileSystemUtils:
    """Test cases for FileSystemUtils."""
    
    def test_calculate_hashes(self, tmp_path):
        """Test hash calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        hashes = FileSystemUtils.calculate_hashes(test_file)
        
        assert 'md5' in hashes
        assert 'sha1' in hashes
        assert 'sha256' in hashes
        assert len(hashes['md5']) == 32
        assert len(hashes['sha1']) == 40
        assert len(hashes['sha256']) == 64
    
    def test_get_file_metadata(self, tmp_path):
        """Test file metadata extraction."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        metadata = FileSystemUtils.get_file_metadata(test_file)
        
        assert 'name' in metadata
        assert 'size' in metadata
        assert 'created' in metadata
        assert 'modified' in metadata
        assert metadata['name'] == "test.txt"
    
    def test_ensure_directory(self, tmp_path):
        """Test directory creation."""
        test_dir = tmp_path / "test" / "nested" / "dir"
        
        result = FileSystemUtils.ensure_directory(test_dir)
        
        assert result.exists()
        assert result.is_dir()
    
    def test_safe_write_read(self, tmp_path):
        """Test safe file write and read."""
        test_file = tmp_path / "test.txt"
        content = "test content"
        
        FileSystemUtils.safe_write(test_file, content)
        read_content = FileSystemUtils.safe_read(test_file)
        
        assert read_content == content



