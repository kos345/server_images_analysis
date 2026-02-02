"""Filesystem utility functions for forensic toolkit."""

import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime


class FileSystemUtils:
    """Utility class for filesystem operations."""
    
    @staticmethod
    def calculate_hashes(file_path: Path) -> Dict[str, str]:
        """
        Calculate MD5, SHA1, and SHA256 hashes of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with hash types as keys and hash values as values
        """
        hashes = {
            'md5': hashlib.md5(),
            'sha1': hashlib.sha1(),
            'sha256': hashlib.sha256()
        }
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    for hash_obj in hashes.values():
                        hash_obj.update(chunk)
            
            return {
                'md5': hashes['md5'].hexdigest(),
                'sha1': hashes['sha1'].hexdigest(),
                'sha256': hashes['sha256'].hexdigest()
            }
        except Exception as e:
            raise IOError(f"Error calculating hashes for {file_path}: {e}")
    
    @staticmethod
    def get_file_metadata(file_path: Path) -> Dict:
        """
        Get file metadata including timestamps and size.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file metadata
        """
        try:
            stat = file_path.stat()
            return {
                'name': file_path.name,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat()
            }
        except Exception as e:
            raise IOError(f"Error getting metadata for {file_path}: {e}")
    
    @staticmethod
    def ensure_directory(directory: Path) -> Path:
        """
        Ensure directory exists, create if necessary.
        
        Args:
            directory: Path to directory
            
        Returns:
            Path object of the directory
        """
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    
    @staticmethod
    def safe_write(file_path: Path, content: str, mode: str = 'w') -> bool:
        """
        Safely write content to file.
        
        Args:
            file_path: Path to file
            content: Content to write
            mode: Write mode ('w' or 'a')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            raise IOError(f"Error writing to {file_path}: {e}")
    
    @staticmethod
    def safe_read(file_path: Path) -> Optional[str]:
        """
        Safely read content from file.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content or None if error
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return None



