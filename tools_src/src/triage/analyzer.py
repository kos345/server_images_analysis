"""Triage analyzer module for artifact analysis and report generation."""

import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from src.utils.logger import get_logger
from src.utils.filesystem import FileSystemUtils


class TriageAnalyzer:
    """
    Analyzer for triage artifacts.
    
    Analyzes collected artifacts and generates HTML reports.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize TriageAnalyzer.
        
        Args:
            log_dir: Directory for log files
        """
        self.logger = get_logger(self.__class__.__name__, log_dir)
        self.fs_utils = FileSystemUtils()
    
    def load_triage_data(self, triage_dir: Path) -> Dict:
        """
        Load all triage data from directory.
        
        Args:
            triage_dir: Path to triage output directory
            
        Returns:
            Dictionary with loaded triage data
        """
        self.logger.info(f"Loading triage data from: {triage_dir}")
        
        data = {
            'os_info': None,
            'users': {'passwd': None, 'shadow': None},
            'history': {},
            'services': None,
            'cron': None,
            'packages': None,
            'iocs': []
        }
        
        try:
            # OS info
            os_file = triage_dir / "system" / "OS.txt"
            if os_file.exists():
                data['os_info'] = self.fs_utils.safe_read(os_file)
            
            # Users
            passwd_file = triage_dir / "users" / "passwd.txt"
            if passwd_file.exists():
                data['users']['passwd'] = self.fs_utils.safe_read(passwd_file)
            
            shadow_file = triage_dir / "users" / "shadow.txt"
            if shadow_file.exists():
                data['users']['shadow'] = self.fs_utils.safe_read(shadow_file)
            
            # History
            history_dir = triage_dir / "users"
            if history_dir.exists():
                for hist_file in history_dir.glob("history_clear_*.txt"):
                    user = hist_file.stem.replace("history_clear_", "")
                    data['history'][user] = self.fs_utils.safe_read(hist_file)
            
            # Services
            services_file = triage_dir / "system" / "services.txt"
            if services_file.exists():
                data['services'] = self.fs_utils.safe_read(services_file)
            
            # Cron
            cron_file = triage_dir / "system" / "cron.txt"
            if cron_file.exists():
                data['cron'] = self.fs_utils.safe_read(cron_file)
            
            # Packages
            packages_file = triage_dir / "system" / "apt.txt"
            if packages_file.exists():
                data['packages'] = self.fs_utils.safe_read(packages_file)
            
            # IOCs
            ioc_file = triage_dir / "files" / "iocs.json"
            if ioc_file.exists():
                try:
                    ioc_content = self.fs_utils.safe_read(ioc_file)
                    if ioc_content:
                        data['iocs'] = json.loads(ioc_content)
                except Exception as e:
                    self.logger.warning(f"Error loading IOCs: {e}")
            
            self.logger.info("Triage data loaded successfully")
            return data
            
        except Exception as e:
            self.logger.exception(f"Error loading triage data: {e}")
            return data
    
    def analyze_artifacts(self, triage_data: Dict) -> Dict:
        """
        Analyze triage artifacts and generate insights.
        
        Args:
            triage_data: Dictionary with triage data
            
        Returns:
            Dictionary with analysis results
        """
        self.logger.info("Analyzing artifacts")
        
        analysis = {
            'summary': {},
            'findings': [],
            'statistics': {}
        }
        
        # Analyze users
        if triage_data.get('users', {}).get('passwd'):
            users = self._parse_passwd(triage_data['users']['passwd'])
            analysis['statistics']['total_users'] = len(users)
            analysis['statistics']['users'] = users
        
        # Analyze history
        if triage_data.get('history'):
            total_commands = sum(len(h.split('\n')) for h in triage_data['history'].values() if h)
            analysis['statistics']['total_commands'] = total_commands
            analysis['statistics']['users_with_history'] = len(triage_data['history'])
        
        # Analyze IOCs
        if triage_data.get('iocs'):
            analysis['statistics']['total_files'] = len(triage_data['iocs'])
            analysis['statistics']['total_iocs'] = len(triage_data['iocs'])
        
        # Analyze services
        if triage_data.get('services'):
            services = self._parse_services(triage_data['services'])
            analysis['statistics']['total_services'] = len(services)
        
        # Generate summary
        analysis['summary'] = self._generate_summary(analysis['statistics'])
        
        return analysis
    
    def _parse_passwd(self, passwd_content: str) -> List[Dict]:
        """Parse /etc/passwd content."""
        users = []
        for line in passwd_content.split('\n'):
            if line and not line.startswith('#'):
                parts = line.split(':')
                if len(parts) >= 7:
                    users.append({
                        'username': parts[0],
                        'uid': parts[2],
                        'gid': parts[3],
                        'home': parts[5],
                        'shell': parts[6]
                    })
        return users
    
    def _parse_services(self, services_content: str) -> List[str]:
        """Parse services content."""
        services = []
        for line in services_content.split('\n'):
            if line and not line.startswith('===') and line.strip():
                services.append(line.strip())
        return services
    
    def _generate_summary(self, statistics: Dict) -> Dict:
        """Generate summary from statistics."""
        return {
            'total_users': statistics.get('total_users', 0),
            'total_commands': statistics.get('total_commands', 0),
            'total_files': statistics.get('total_files', 0),
            'total_services': statistics.get('total_services', 0),
            'analysis_date': datetime.now().isoformat()
        }
    
    def generate_html_report(self, triage_dir: Path, triage_data: Dict, analysis: Dict) -> Path:
        """
        Generate HTML report from triage data and analysis.
        
        Args:
            triage_dir: Path to triage output directory
            triage_data: Loaded triage data
            analysis: Analysis results
            
        Returns:
            Path to generated HTML report
        """
        self.logger.info("Generating HTML report")
        
        html_file = triage_dir / "report.html"
        
        html_content = self._build_html(triage_data, analysis)
        self.fs_utils.safe_write(html_file, html_content)
        
        self.logger.info(f"HTML report generated: {html_file}")
        return html_file
    
    def _build_html(self, triage_data: Dict, analysis: Dict) -> str:
        """Build HTML content."""
        summary = analysis.get('summary', {})
        stats = analysis.get('statistics', {})
        
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forensic Triage Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary {{
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .stat {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
        }}
        .stat-label {{
            font-weight: bold;
            color: #666;
        }}
        .stat-value {{
            font-size: 24px;
            color: #4CAF50;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .code-block {{
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: monospace;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Forensic Triage Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <h2>Summary</h2>
            <div class="stat">
                <div class="stat-label">Total Users</div>
                <div class="stat-value">{summary.get('total_users', 0)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Total Commands</div>
                <div class="stat-value">{summary.get('total_commands', 0)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Total Files</div>
                <div class="stat-value">{summary.get('total_files', 0)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Total Services</div>
                <div class="stat-value">{summary.get('total_services', 0)}</div>
            </div>
        </div>
"""
        
        # Users section
        if stats.get('users'):
            html += "<h2>Users</h2><table><tr><th>Username</th><th>UID</th><th>Home</th><th>Shell</th></tr>"
            for user in stats['users']:
                html += f"<tr><td>{user['username']}</td><td>{user['uid']}</td><td>{user['home']}</td><td>{user['shell']}</td></tr>"
            html += "</table>"
        
        # IOCs section
        if triage_data.get('iocs'):
            html += "<h2>Indicators of Compromise (IOCs)</h2>"
            html += f"<p>Total IOCs: {len(triage_data['iocs'])}</p>"
            html += "<table><tr><th>Name</th><th>Size</th><th>MD5</th><th>SHA256</th><th>Modified</th></tr>"
            for ioc in triage_data['iocs'][:50]:  # Limit display
                html += f"<tr><td>{ioc.get('name', 'N/A')}</td>"
                html += f"<td>{ioc.get('size', 0)}</td>"
                html += f"<td><code>{ioc.get('md5', 'N/A')[:16]}...</code></td>"
                html += f"<td><code>{ioc.get('sha256', 'N/A')[:32]}...</code></td>"
                html += f"<td>{ioc.get('modified', 'N/A')}</td></tr>"
            html += "</table>"
        
        # History section
        if triage_data.get('history'):
            html += "<h2>Command History</h2>"
            for user, history in triage_data['history'].items():
                if history:
                    lines = history.split('\n')[:20]  # Limit display
                    html += f"<h3>User: {user}</h3>"
                    html += f"<div class='code-block'>{'<br>'.join(lines)}</div>"
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def generate_summary(self, analysis: Dict) -> str:
        """
        Generate brief text summary.
        
        Args:
            analysis: Analysis results
            
        Returns:
            Text summary string
        """
        summary = analysis.get('summary', {})
        stats = analysis.get('statistics', {})
        
        summary_text = f"""
Forensic Triage Analysis Summary
================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Statistics:
- Total Users: {summary.get('total_users', 0)}
- Total Commands: {summary.get('total_commands', 0)}
- Total Files: {summary.get('total_files', 0)}
- Total Services: {summary.get('total_services', 0)}
- Users with History: {stats.get('users_with_history', 0)}

Analysis completed successfully.
"""
        return summary_text
    
    def prepare_telegram_data(self, triage_dir: Path, analysis: Dict) -> Dict:
        """
        Prepare data for Telegram bot.
        
        Args:
            triage_dir: Path to triage output directory
            analysis: Analysis results
            
        Returns:
            Dictionary with Telegram-ready data
        """
        summary = analysis.get('summary', {})
        
        return {
            'summary': summary,
            'report_path': str(triage_dir / "report.html"),
            'ioc_path': str(triage_dir / "files" / "iocs.json"),
            'message': self.generate_summary(analysis)
        }



