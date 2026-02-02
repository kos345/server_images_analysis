"""Image processor module for handling forensic disk images."""

import subprocess
import os
from pathlib import Path
from typing import Optional, Dict
from src.utils.logger import get_logger
from src.utils.filesystem import FileSystemUtils


class ImageProcessor:
    """
    Processor for forensic disk images.
    
    Handles image type detection, RAW conversion, and metadata extraction.
    """
    
    # Supported image formats
    SUPPORTED_FORMATS = {
        'raw', 'dd', 'img', 'vmdk', 'vdi', 'vhd', 'vhdx', 
        'qcow2', 'qcow', 'vpc', 'vhdx'
    }
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize ImageProcessor.
        
        Args:
            log_dir: Directory for log files
        """
        self.logger = get_logger(self.__class__.__name__, log_dir)
        self.fs_utils = FileSystemUtils()
    
    def detect_image_type(self, image_path: Path) -> Optional[str]:
        """
        Detect the type of disk image.
        
        Args:
            image_path: Path to the disk image
            
        Returns:
            Image format string or None if unknown
        """
        self.logger.info(f"Detecting image type for: {image_path}")
        
        if not image_path.exists():
            self.logger.error(f"Image file not found: {image_path}")
            return None
        
        # Check by extension
        ext = image_path.suffix.lower().lstrip('.')
        if ext in self.SUPPORTED_FORMATS:
            self.logger.info(f"Detected format by extension: {ext}")
            return ext
        
        # Try to detect using qemu-img
        try:
            result = subprocess.run(
                ['qemu-img', 'info', str(image_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'file format:' in line.lower():
                        format_name = line.split(':')[-1].strip()
                        self.logger.info(f"Detected format by qemu-img: {format_name}")
                        return format_name
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.warning(f"Could not detect format using qemu-img: {e}")
        
        self.logger.warning(f"Unknown image format for: {image_path}")
        return None
    
    def is_raw(self, image_path: Path) -> bool:
        """
        Check if image is already in RAW format.
        
        Args:
            image_path: Path to the disk image
            
        Returns:
            True if RAW format, False otherwise
        """
        image_type = self.detect_image_type(image_path)
        return image_type in ('raw', 'dd', 'img')
    
    def convert_to_raw(self, image_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Convert disk image to RAW format using qemu-img.
        
        Args:
            image_path: Path to source image
            output_path: Path for output RAW file (optional)
            
        Returns:
            Path to converted RAW file or None if error
        """
        self.logger.info(f"Converting image to RAW: {image_path}")
        
        if self.is_raw(image_path):
            self.logger.info("Image is already in RAW format")
            return image_path
        
        if output_path is None:
            output_path = image_path.parent / f"{image_path.stem}.raw"
        
        try:
            self.logger.info(f"Output RAW file: {output_path}")
            
            result = subprocess.run(
                ['qemu-img', 'convert', '-f', 'auto', '-O', 'raw', 
                 str(image_path), str(output_path)],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully converted to RAW: {output_path}")
                return output_path
            else:
                self.logger.error(f"Conversion failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Conversion timeout exceeded")
            return None
        except FileNotFoundError:
            self.logger.error("qemu-img not found. Please install QEMU tools.")
            return None
        except Exception as e:
            self.logger.exception(f"Error during conversion: {e}")
            return None
    
    def get_metadata(self, image_path: Path) -> Dict:
        """
        Collect metadata about the disk image.
        
        Args:
            image_path: Path to the disk image
            
        Returns:
            Dictionary with image metadata
        """
        self.logger.info(f"Collecting metadata for: {image_path}")
        
        metadata = {
            'path': str(image_path),
            'name': image_path.name,
            'type': self.detect_image_type(image_path),
            'is_raw': self.is_raw(image_path),
            'raw_path': None
        }
        
        # Get file metadata
        try:
            file_meta = self.fs_utils.get_file_metadata(image_path)
            metadata.update(file_meta)
        except Exception as e:
            self.logger.warning(f"Could not get file metadata: {e}")
        
        # Get hashes
        try:
            hashes = self.fs_utils.calculate_hashes(image_path)
            metadata['hashes'] = hashes
        except Exception as e:
            self.logger.warning(f"Could not calculate hashes: {e}")
        
        # Convert to RAW if needed and get RAW path
        if not metadata['is_raw']:
            raw_path = self.convert_to_raw(image_path)
            if raw_path:
                metadata['raw_path'] = str(raw_path)
                try:
                    raw_meta = self.fs_utils.get_file_metadata(raw_path)
                    metadata['raw_size'] = raw_meta['size']
                except Exception as e:
                    self.logger.warning(f"Could not get RAW metadata: {e}")
        else:
            metadata['raw_path'] = str(image_path)
        
        return metadata



