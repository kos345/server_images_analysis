"""Main entry point for Forensic Image Triage & Analysis Toolkit."""

import argparse
import sys
from pathlib import Path
from src.utils.logger import get_logger
from src.core.image_processor import ImageProcessor
from src.triage.collector import TriageCollector
from src.triage.analyzer import TriageAnalyzer
from src.triage.context_enricher import ContextEnricher
from src.integrations.telegram_bot import TelegramBot


class ForensicTriageToolkit:
    """
    Main class for forensic triage toolkit.
    
    Orchestrates the complete triage workflow.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize toolkit.
        
        Args:
            log_dir: Directory for log files
        """
        self.logger = get_logger(self.__class__.__name__, log_dir)
        self.image_processor = ImageProcessor(log_dir)
        self.triage_collector = TriageCollector(log_dir=log_dir)
        self.triage_analyzer = TriageAnalyzer(log_dir)
        self.context_enricher = ContextEnricher(log_dir)
        self.telegram_bot = TelegramBot(log_dir=log_dir)
    
    def process_image(self, image_path: Path) -> dict:
        """
        Process disk image.
        
        Args:
            image_path: Path to disk image
            
        Returns:
            Dictionary with image metadata
        """
        self.logger.info(f"Processing image: {image_path}")
        return self.image_processor.get_metadata(image_path)
    
    def run_triage(self, image_path: Path, image_name: str = None) -> Path:
        """
        Run complete triage workflow.
        
        Args:
            image_path: Path to disk image
            image_name: Optional name for the image
            
        Returns:
            Path to triage output directory
        """
        self.logger.info("Starting triage workflow")
        
        # Process image
        metadata = self.process_image(image_path)
        raw_path = Path(metadata.get('raw_path', image_path))
        
        if not raw_path or not raw_path.exists():
            self.logger.error("RAW image not available")
            return None
        
        # Collect triage
        if image_name is None:
            image_name = Path(image_path).stem
        
        triage_dir = self.triage_collector.collect_all(raw_path, image_name)
        
        if not triage_dir:
            self.logger.error("Triage collection failed")
            return None
        
        # Analyze
        triage_data = self.triage_analyzer.load_triage_data(triage_dir)
        analysis = self.triage_analyzer.analyze_artifacts(triage_data)
        report_path = self.triage_analyzer.generate_html_report(triage_dir, triage_data, analysis)
        
        # Generate summary
        summary = self.triage_analyzer.generate_summary(analysis)
        self.logger.info(f"Analysis summary:\n{summary}")
        
        # Enrich context
        enriched_file = self.context_enricher.enrich_triage(triage_dir)
        
        # Prepare Telegram data
        telegram_data = self.triage_analyzer.prepare_telegram_data(triage_dir, analysis)
        
        # Send to Telegram if configured
        if self.telegram_bot.bot_token and self.telegram_bot.chat_id:
            self.telegram_bot.send_triage_results(telegram_data)
        
        self.logger.info(f"Triage workflow completed: {triage_dir}")
        return triage_dir


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Forensic Image Triage & Analysis Toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process and triage a disk image
  python -m src.main --image disk.img --triage
  
  # Process image only
  python -m src.main --image disk.img
  
  # Triage with custom name
  python -m src.main --image disk.img --triage --name my_analysis
        """
    )
    
    parser.add_argument(
        '--image',
        type=str,
        required=True,
        help='Path to disk image file'
    )
    
    parser.add_argument(
        '--triage',
        action='store_true',
        help='Run complete triage workflow'
    )
    
    parser.add_argument(
        '--name',
        type=str,
        default=None,
        help='Custom name for triage analysis'
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Directory for log files (default: logs)'
    )
    
    args = parser.parse_args()
    
    # Validate image path
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    # Initialize toolkit
    toolkit = ForensicTriageToolkit(log_dir=args.log_dir)
    
    try:
        if args.triage:
            # Run complete triage workflow
            triage_dir = toolkit.run_triage(image_path, args.name)
            if triage_dir:
                print(f"\n✓ Triage completed successfully!")
                print(f"  Output directory: {triage_dir}")
                print(f"  Report: {triage_dir / 'report.html'}")
                sys.exit(0)
            else:
                print("\n✗ Triage failed. Check logs for details.")
                sys.exit(1)
        else:
            # Process image only
            metadata = toolkit.process_image(image_path)
            print("\n✓ Image processed successfully!")
            print(f"  Type: {metadata.get('type', 'unknown')}")
            print(f"  Size: {metadata.get('size', 0)} bytes")
            print(f"  RAW path: {metadata.get('raw_path', 'N/A')}")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        toolkit.logger.exception("Unhandled exception")
        sys.exit(1)


if __name__ == '__main__':
    main()



