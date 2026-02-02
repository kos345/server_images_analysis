"""Telegram bot integration for sending triage reports."""

import os
from pathlib import Path
from typing import Optional, List
from src.utils.logger import get_logger


class TelegramBot:
    """
    Telegram bot for sending forensic triage reports.
    
    Sends text messages, files, and reports to Telegram.
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, log_dir: str = "logs"):
        """
        Initialize TelegramBot.
        
        Args:
            bot_token: Telegram bot token (from environment or parameter)
            chat_id: Telegram chat ID (from environment or parameter)
            log_dir: Directory for log files
        """
        self.logger = get_logger(self.__class__.__name__, log_dir)
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram bot token or chat ID not configured")
    
    def send_message(self, message: str) -> bool:
        """
        Send text message to Telegram.
        
        Args:
            message: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            self.logger.error("Telegram not configured")
            return False
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            self.logger.info("Message sent to Telegram")
            return True
            
        except ImportError:
            self.logger.error("requests library not installed")
            return False
        except Exception as e:
            self.logger.exception(f"Error sending message to Telegram: {e}")
            return False
    
    def send_file(self, file_path: Path, caption: Optional[str] = None) -> bool:
        """
        Send file to Telegram.
        
        Args:
            file_path: Path to file to send
            caption: Optional caption for the file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            self.logger.error("Telegram not configured")
            return False
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return False
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
            
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption or file_path.name
                }
                
                response = requests.post(url, files=files, data=data, timeout=60)
                response.raise_for_status()
            
            self.logger.info(f"File sent to Telegram: {file_path.name}")
            return True
            
        except ImportError:
            self.logger.error("requests library not installed")
            return False
        except Exception as e:
            self.logger.exception(f"Error sending file to Telegram: {e}")
            return False
    
    def send_report(self, report_path: Path, ioc_path: Optional[Path] = None, summary: Optional[str] = None) -> bool:
        """
        Send complete triage report to Telegram.
        
        Args:
            report_path: Path to HTML report
            ioc_path: Optional path to IOC JSON file
            summary: Optional summary text
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Sending report to Telegram")
        
        success = True
        
        # Send summary
        if summary:
            success &= self.send_message(summary)
        
        # Send HTML report
        if report_path.exists():
            success &= self.send_file(report_path, caption="Forensic Triage Report")
        else:
            self.logger.warning(f"Report file not found: {report_path}")
        
        # Send IOC file
        if ioc_path and ioc_path.exists():
            success &= self.send_file(ioc_path, caption="Indicators of Compromise (IOCs)")
        
        return success
    
    def send_triage_results(self, triage_data: dict) -> bool:
        """
        Send triage results using prepared Telegram data.
        
        Args:
            triage_data: Dictionary with Telegram-ready data (from TriageAnalyzer)
            
        Returns:
            True if successful, False otherwise
        """
        report_path = Path(triage_data.get('report_path', ''))
        ioc_path = Path(triage_data.get('ioc_path', '')) if triage_data.get('ioc_path') else None
        message = triage_data.get('message', '')
        
        return self.send_report(report_path, ioc_path, message)



