"""Triage collector module for artifact collection from disk images."""

import pytsk3
import uuid
import yaml
import json
import gzip
import tarfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from src.utils.logger import get_logger
from src.utils.filesystem import FileSystemUtils


class TriageCollector:
    """
    Collector for forensic artifacts from disk images.
    
    Uses pytsk3 to extract filesystem artifacts from Linux systems.
    """
    
    def __init__(self, config_path: str = "configs/triage.yaml", log_dir: str = "logs"):
        """
        Initialize TriageCollector.
        
        Args:
            config_path: Path to triage configuration file
            log_dir: Directory for log files
        """
        self.logger = get_logger(self.__class__.__name__, log_dir)
        self.fs_utils = FileSystemUtils()
        self.config = self._load_config(config_path)
        self.image_handle = None
        self.fs_handle = None
        self.output_dir = None
    
    def _load_config(self, config_path: str) -> Dict:
        """Load triage configuration from YAML file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            else:
                self.logger.warning(f"Config file not found: {config_path}, using defaults")
                return self._get_default_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            'artifacts': {
                'system': ['/etc/os-release', '/etc/issue'],
                'users': ['/etc/passwd', '/etc/shadow'],
                'history': ['/home/*/.bash_history', '/root/.bash_history'],
                'services': ['/etc/systemd/system', '/etc/init.d'],
                'cron': ['/etc/crontab', '/var/spool/cron'],
                'packages': ['/var/lib/dpkg/status'],
                'logs': {
                    'var': ['/var/log'],
                    'www': ['/var/www']
                },
                'docker': ['/var/lib/docker']
            }
        }
    
    def open_image(self, image_path: Path) -> bool:
        """
        Open disk image for reading.
        
        Args:
            image_path: Path to RAW disk image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Opening image: {image_path}")
            self.image_handle = pytsk3.Img_Info(str(image_path))
            self.fs_handle = pytsk3.FS_Info(self.image_handle)
            self.logger.info("Image opened successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Error opening image: {e}")
            return False
    
    def detect_os(self) -> Optional[str]:
        """
        Detect operating system from disk image.
        
        Returns:
            OS name or None if detection fails
        """
        try:
            self.logger.info("Detecting operating system")
            
            # Try to read /etc/os-release
            os_release = self._read_file('/etc/os-release')
            if os_release:
                for line in os_release.split('\n'):
                    if line.startswith('ID='):
                        os_name = line.split('=')[1].strip().strip('"')
                        self.logger.info(f"Detected OS: {os_name}")
                        return os_name.lower()
            
            # Try /etc/issue as fallback
            issue = self._read_file('/etc/issue')
            if issue and 'linux' in issue.lower():
                self.logger.info("Detected OS: Linux (from /etc/issue)")
                return 'linux'
            
            self.logger.warning("Could not detect OS")
            return None
        except Exception as e:
            self.logger.exception(f"Error detecting OS: {e}")
            return None
    
    def _read_file(self, file_path: str) -> Optional[str]:
        """
        Read file from filesystem image.
        
        Args:
            file_path: Path to file in image
            
        Returns:
            File content or None if error
        """
        try:
            file_obj = self.fs_handle.open(file_path)
            if file_obj:
                content = file_obj.read_random(0, file_obj.get_size())
                return content.decode('utf-8', errors='ignore')
        except Exception as e:
            self.logger.debug(f"Could not read {file_path}: {e}")
        return None
    
    def _list_directory(self, dir_path: str) -> List[str]:
        """
        List files in directory.
        
        Args:
            dir_path: Path to directory
            
        Returns:
            List of file paths
        """
        files = []
        try:
            directory = self.fs_handle.open_dir(dir_path)
            if directory:
                for entry in directory:
                    if entry.info.name.name not in ['.', '..']:
                        full_path = f"{dir_path.rstrip('/')}/{entry.info.name.name}"
                        files.append(full_path)
        except Exception as e:
            self.logger.debug(f"Could not list {dir_path}: {e}")
        return files
    
    def create_output_directory(self, image_name: str) -> Path:
        """
        Create output directory for triage results.
        
        Args:
            image_name: Name of the image
            
        Returns:
            Path to output directory
        """
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        uuid_str = str(uuid.uuid4())[:8]
        dir_name = f"{image_name}_{date_str}_{uuid_str}"
        self.output_dir = Path("triage") / dir_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created output directory: {self.output_dir}")
        return self.output_dir
    
    def collect_os_info(self):
        """Collect operating system information."""
        self.logger.info("Collecting OS information")
        output_file = self.output_dir / "system" / "OS.txt"
        self.fs_utils.ensure_directory(output_file.parent)
        
        content = []
        for path in self.config.get('artifacts', {}).get('system', []):
            file_content = self._read_file(path)
            if file_content:
                content.append(f"=== {path} ===\n{file_content}\n")
        
        self.fs_utils.safe_write(output_file, '\n'.join(content))
    
    def collect_users(self):
        """Collect user information (passwd and shadow)."""
        self.logger.info("Collecting user information")
        
        # passwd
        passwd_content = self._read_file('/etc/passwd')
        if passwd_content:
            output_file = self.output_dir / "users" / "passwd.txt"
            self.fs_utils.ensure_directory(output_file.parent)
            self.fs_utils.safe_write(output_file, passwd_content)
        
        # shadow
        shadow_content = self._read_file('/etc/shadow')
        if shadow_content:
            output_file = self.output_dir / "users" / "shadow.txt"
            self.fs_utils.ensure_directory(output_file.parent)
            self.fs_utils.safe_write(output_file, shadow_content)
    
    def collect_history(self):
        """Collect command history files."""
        self.logger.info("Collecting command history")
        
        # Get users from passwd
        passwd_content = self._read_file('/etc/passwd')
        if not passwd_content:
            return
        
        users = []
        for line in passwd_content.split('\n'):
            if ':' in line:
                username = line.split(':')[0]
                users.append(username)
        
        # Collect history for each user
        for user in users:
            history_paths = [
                f'/home/{user}/.bash_history',
                f'/home/{user}/.zsh_history',
                f'/root/.bash_history' if user == 'root' else None
            ]
            
            for hist_path in history_paths:
                if hist_path:
                    content = self._read_file(hist_path)
                    if content:
                        output_file = self.output_dir / "users" / f"history_{user}.txt"
                        self.fs_utils.ensure_directory(output_file.parent)
                        self.fs_utils.safe_write(output_file, content, mode='a')
    
    def clean_history(self):
        """Remove duplicates from history files."""
        self.logger.info("Cleaning history files")
        history_dir = self.output_dir / "users"
        
        if not history_dir.exists():
            return
        
        for hist_file in history_dir.glob("history_*.txt"):
            if hist_file.name.startswith("history_clear_"):
                continue
            
            try:
                content = self.fs_utils.safe_read(hist_file)
                if content:
                    lines = content.split('\n')
                    unique_lines = list(dict.fromkeys(lines))  # Preserve order, remove duplicates
                    
                    user = hist_file.stem.replace("history_", "")
                    output_file = history_dir / f"history_clear_{user}.txt"
                    self.fs_utils.safe_write(output_file, '\n'.join(unique_lines))
            except Exception as e:
                self.logger.warning(f"Error cleaning {hist_file}: {e}")
    
    def collect_services(self):
        """Collect system services information."""
        self.logger.info("Collecting services information")
        output_file = self.output_dir / "system" / "services.txt"
        self.fs_utils.ensure_directory(output_file.parent)
        
        content = []
        service_paths = ['/etc/systemd/system', '/etc/init.d']
        
        for service_path in service_paths:
            files = self._list_directory(service_path)
            content.append(f"=== {service_path} ===\n")
            content.extend(files)
            content.append("")
        
        self.fs_utils.safe_write(output_file, '\n'.join(content))
    
    def collect_cron(self):
        """Collect cron information."""
        self.logger.info("Collecting cron information")
        output_file = self.output_dir / "system" / "cron.txt"
        self.fs_utils.ensure_directory(output_file.parent)
        
        content = []
        cron_paths = ['/etc/crontab', '/var/spool/cron']
        
        for cron_path in cron_paths:
            cron_content = self._read_file(cron_path)
            if cron_content:
                content.append(f"=== {cron_path} ===\n{cron_content}\n")
        
        self.fs_utils.safe_write(output_file, '\n'.join(content))
    
    def collect_packages(self):
        """Collect installed packages information."""
        self.logger.info("Collecting packages information")
        output_file = self.output_dir / "system" / "apt.txt"
        self.fs_utils.ensure_directory(output_file.parent)
        
        pkg_content = self._read_file('/var/lib/dpkg/status')
        if pkg_content:
            self.fs_utils.safe_write(output_file, pkg_content)
    
    def collect_logs(self):
        """Collect log files."""
        self.logger.info("Collecting log files")
        
        # Create log lists
        var_logs = []
        www_logs = []
        
        # List var/log directory
        var_files = self._list_directory('/var/log')
        var_logs.extend(var_files)
        
        # List www logs if exists
        www_files = self._list_directory('/var/www')
        www_logs.extend(www_files)
        
        # Save lists
        var_list_file = self.output_dir / "logs" / "var.txt"
        self.fs_utils.ensure_directory(var_list_file.parent)
        self.fs_utils.safe_write(var_list_file, '\n'.join(var_logs))
        
        www_list_file = self.output_dir / "logs" / "www.txt"
        self.fs_utils.ensure_directory(www_list_file.parent)
        self.fs_utils.safe_write(www_list_file, '\n'.join(www_logs))
        
        # Extract log files
        self._extract_logs(var_logs, self.output_dir / "logs" / "raw" / "var")
        self._extract_logs(www_logs, self.output_dir / "logs" / "raw" / "www")
    
    def _extract_logs(self, log_paths: List[str], output_dir: Path):
        """Extract log files to output directory."""
        self.fs_utils.ensure_directory(output_dir)
        
        for log_path in log_paths[:100]:  # Limit to prevent too many files
            try:
                content = self._read_file(log_path)
                if content:
                    safe_name = log_path.replace('/', '_').lstrip('_')
                    output_file = output_dir / safe_name
                    self.fs_utils.safe_write(output_file, content)
            except Exception as e:
                self.logger.debug(f"Could not extract {log_path}: {e}")
    
    def collect_auth_logs(self):
        """Collect and merge authentication logs."""
        self.logger.info("Collecting authentication logs")
        
        auth_logs = []
        auth_files = [
            '/var/log/auth.log',
            '/var/log/secure',
            '/var/log/messages'
        ]
        
        for auth_file in auth_files:
            content = self._read_file(auth_file)
            if content:
                # Handle compressed logs
                if auth_file.endswith('.gz'):
                    try:
                        content = gzip.decompress(content).decode('utf-8', errors='ignore')
                    except:
                        continue
                auth_logs.append(f"=== {auth_file} ===\n{content}\n")
        
        if auth_logs:
            output_file = self.output_dir / "logs" / "clear" / "auth_full.log"
            self.fs_utils.ensure_directory(output_file.parent)
            self.fs_utils.safe_write(output_file, '\n'.join(auth_logs))
    
    def collect_docker_info(self):
        """Collect Docker information."""
        self.logger.info("Collecting Docker information")
        output_file = self.output_dir / "system" / "docker.txt"
        self.fs_utils.ensure_directory(output_file.parent)
        
        docker_paths = ['/var/lib/docker', '/etc/docker']
        content = []
        
        for docker_path in docker_paths:
            files = self._list_directory(docker_path)
            content.append(f"=== {docker_path} ===\n")
            content.extend(files[:50])  # Limit output
            content.append("")
        
        self.fs_utils.safe_write(output_file, '\n'.join(content))
    
    def extract_home_files(self):
        """Extract files from home and root directories."""
        self.logger.info("Extracting home/root files")
        output_dir = self.output_dir / "files" / "raw"
        self.fs_utils.ensure_directory(output_dir)
        
        home_dirs = ['/home', '/root']
        
        for home_dir in home_dirs:
            files = self._list_directory(home_dir)
            for file_path in files[:200]:  # Limit files
                try:
                    content = self._read_file(file_path)
                    if content:
                        safe_name = file_path.replace('/', '_').lstrip('_')
                        output_file = output_dir / safe_name
                        self.fs_utils.safe_write(output_file, content)
                except Exception as e:
                    self.logger.debug(f"Could not extract {file_path}: {e}")
    
    def generate_ioc_file(self):
        """Generate IOC (Indicators of Compromise) file."""
        self.logger.info("Generating IOC file")
        ioc_file = self.output_dir / "files" / "iocs.json"
        self.fs_utils.ensure_directory(ioc_file.parent)
        
        iocs = []
        files_dir = self.output_dir / "files" / "raw"
        
        if files_dir.exists():
            for file_path in files_dir.iterdir():
                if file_path.is_file():
                    try:
                        metadata = self.fs_utils.get_file_metadata(file_path)
                        hashes = self.fs_utils.calculate_hashes(file_path)
                        
                        ioc = {
                            'name': metadata['name'],
                            'type': 'file',
                            'created': metadata['created'],
                            'modified': metadata['modified'],
                            'size': metadata['size'],
                            'md5': hashes['md5'],
                            'sha1': hashes['sha1'],
                            'sha256': hashes['sha256']
                        }
                        iocs.append(ioc)
                    except Exception as e:
                        self.logger.debug(f"Error processing {file_path} for IOC: {e}")
        
        self.fs_utils.safe_write(ioc_file, json.dumps(iocs, indent=2))
    
    def collect_all(self, image_path: Path, image_name: str) -> Optional[Path]:
        """
        Perform complete triage collection.
        
        Args:
            image_path: Path to RAW disk image
            image_name: Name identifier for the image
            
        Returns:
            Path to output directory or None if error
        """
        try:
            self.logger.info(f"Starting triage collection for: {image_name}")
            
            # Open image
            if not self.open_image(image_path):
                return None
            
            # Detect OS
            os_name = self.detect_os()
            if not os_name or os_name != 'linux':
                self.logger.error("Only Linux systems are supported")
                return None
            
            # Create output directory
            self.create_output_directory(image_name)
            
            # Collect artifacts
            self.collect_os_info()
            self.collect_users()
            self.collect_history()
            self.clean_history()
            self.collect_services()
            self.collect_cron()
            self.collect_packages()
            self.collect_logs()
            self.collect_auth_logs()
            self.collect_docker_info()
            self.extract_home_files()
            self.generate_ioc_file()
            
            self.logger.info(f"Triage collection completed: {self.output_dir}")
            return self.output_dir
            
        except Exception as e:
            self.logger.exception(f"Error during triage collection: {e}")
            return None
        finally:
            # Cleanup (pytsk3 objects are automatically cleaned up by Python)
            self.fs_handle = None
            self.image_handle = None

