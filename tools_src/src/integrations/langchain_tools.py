"""LangChain tools integration for forensic triage toolkit."""

from typing import Optional, Dict, Any
from pathlib import Path
from src.utils.logger import get_logger
from src.core.image_processor import ImageProcessor
from src.triage.collector import TriageCollector
from src.triage.analyzer import TriageAnalyzer
from src.triage.context_enricher import ContextEnricher


class LangChainTools:
    """
    LangChain tools wrapper for forensic triage operations.
    
    Provides tools that can be used with LangChain agents.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize LangChainTools.
        
        Args:
            log_dir: Directory for log files
        """
        self.logger = get_logger(self.__class__.__name__, log_dir)
        self.image_processor = ImageProcessor(log_dir)
        self.triage_collector = TriageCollector(log_dir=log_dir)
        self.triage_analyzer = TriageAnalyzer(log_dir)
        self.context_enricher = ContextEnricher(log_dir)
    
    def get_tools(self) -> list:
        """
        Get list of LangChain tools.
        
        Returns:
            List of LangChain tool objects
        """
        try:
            from langchain.tools import Tool
        except ImportError:
            self.logger.warning("LangChain not installed, tools not available")
            return []
        
        tools = [
            Tool(
                name="process_image",
                func=self.process_image_tool,
                description="Process a forensic disk image: detect type, convert to RAW if needed, extract metadata"
            ),
            Tool(
                name="collect_triage",
                func=self.collect_triage_tool,
                description="Collect forensic artifacts from a disk image (Linux only)"
            ),
            Tool(
                name="analyze_triage",
                func=self.analyze_triage_tool,
                description="Analyze collected triage artifacts and generate report"
            ),
            Tool(
                name="enrich_context",
                func=self.enrich_context_tool,
                description="Extract and enrich entities (IPs, domains, hashes) from triage data"
            )
        ]
        
        return tools
    
    def process_image_tool(self, image_path: str) -> str:
        """
        Tool for processing disk image.
        
        Args:
            image_path: Path to disk image
            
        Returns:
            JSON string with metadata
        """
        try:
            import json
            image_path_obj = Path(image_path)
            metadata = self.image_processor.get_metadata(image_path_obj)
            return json.dumps(metadata, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def collect_triage_tool(self, image_path: str) -> str:
        """
        Tool for collecting triage artifacts.
        
        Args:
            image_path: Path to RAW disk image
            
        Returns:
            Path to triage output directory
        """
        try:
            image_path_obj = Path(image_path)
            image_name = image_path_obj.stem
            output_dir = self.triage_collector.collect_all(image_path_obj, image_name)
            return str(output_dir) if output_dir else "Error: Triage collection failed"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def analyze_triage_tool(self, triage_dir: str) -> str:
        """
        Tool for analyzing triage data.
        
        Args:
            triage_dir: Path to triage output directory
            
        Returns:
            JSON string with analysis results
        """
        try:
            import json
            triage_dir_obj = Path(triage_dir)
            triage_data = self.triage_analyzer.load_triage_data(triage_dir_obj)
            analysis = self.triage_analyzer.analyze_artifacts(triage_data)
            report_path = self.triage_analyzer.generate_html_report(triage_dir_obj, triage_data, analysis)
            return json.dumps({
                'analysis': analysis,
                'report_path': str(report_path)
            }, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def enrich_context_tool(self, triage_dir: str) -> str:
        """
        Tool for enriching triage context.
        
        Args:
            triage_dir: Path to triage output directory
            
        Returns:
            Path to enriched data file
        """
        try:
            triage_dir_obj = Path(triage_dir)
            enriched_file = self.context_enricher.enrich_triage(triage_dir_obj)
            return str(enriched_file) if enriched_file else "Error: Enrichment failed"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_agent(self, llm) -> Any:
        """
        Create LangChain agent with forensic tools.
        
        Args:
            llm: LangChain LLM instance
            
        Returns:
            LangChain agent
        """
        try:
            from langchain.agents import initialize_agent, AgentType
            from langchain.tools import Tool
            
            tools = self.get_tools()
            
            if not tools:
                raise ImportError("LangChain tools not available")
            
            agent = initialize_agent(
                tools=tools,
                llm=llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True
            )
            
            return agent
        except ImportError as e:
            self.logger.error(f"LangChain not properly installed: {e}")
            return None
        except Exception as e:
            self.logger.exception(f"Error creating agent: {e}")
            return None



