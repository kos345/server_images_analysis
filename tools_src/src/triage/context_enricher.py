"""Context enricher module for entity extraction and data enrichment."""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from src.utils.logger import get_logger
from src.utils.filesystem import FileSystemUtils


class ContextEnricher:
    """
    Enricher for extracting entities and enriching triage data.
    
    Extracts IP addresses, hashes, domains, and enriches with external data.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize ContextEnricher.
        
        Args:
            log_dir: Directory for log files
        """
        self.logger = get_logger(self.__class__.__name__, log_dir)
        self.fs_utils = FileSystemUtils()
        
        # Regex patterns
        self.ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        self.hash_patterns = {
            'md5': re.compile(r'\b[a-fA-F0-9]{32}\b'),
            'sha1': re.compile(r'\b[a-fA-F0-9]{40}\b'),
            'sha256': re.compile(r'\b[a-fA-F0-9]{64}\b')
        }
        self.domain_pattern = re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b')
    
    def extract_entities(self, triage_dir: Path) -> Dict:
        """
        Extract entities from triage data.
        
        Args:
            triage_dir: Path to triage output directory
            
        Returns:
            Dictionary with extracted entities
        """
        self.logger.info("Extracting entities from triage data")
        
        entities = {
            'ips': set(),
            'domains': set(),
            'hashes': {
                'md5': set(),
                'sha1': set(),
                'sha256': set()
            }
        }
        
        # Extract from all text files
        for file_path in triage_dir.rglob("*.txt"):
            try:
                content = self.fs_utils.safe_read(file_path)
                if content:
                    self._extract_from_text(content, entities)
            except Exception as e:
                self.logger.debug(f"Error processing {file_path}: {e}")
        
        # Extract from log files
        log_dir = triage_dir / "logs" / "raw"
        if log_dir.exists():
            for log_file in log_dir.rglob("*"):
                if log_file.is_file():
                    try:
                        content = self.fs_utils.safe_read(log_file)
                        if content:
                            self._extract_from_text(content, entities)
                    except Exception as e:
                        self.logger.debug(f"Error processing {log_file}: {e}")
        
        # Convert sets to lists for JSON serialization
        result = {
            'ips': sorted(list(entities['ips'])),
            'domains': sorted(list(entities['domains'])),
            'hashes': {
                'md5': sorted(list(entities['hashes']['md5'])),
                'sha1': sorted(list(entities['hashes']['sha1'])),
                'sha256': sorted(list(entities['hashes']['sha256']))
            }
        }
        
        self.logger.info(f"Extracted {len(result['ips'])} IPs, {len(result['domains'])} domains, "
                        f"{len(result['hashes']['md5']) + len(result['hashes']['sha1']) + len(result['hashes']['sha256'])} hashes")
        
        return result
    
    def _extract_from_text(self, text: str, entities: Dict):
        """Extract entities from text content."""
        # Extract IPs
        ips = self.ip_pattern.findall(text)
        entities['ips'].update(ips)
        
        # Extract domains
        domains = self.domain_pattern.findall(text)
        entities['domains'].update(domains)
        
        # Extract hashes
        for hash_type, pattern in self.hash_patterns.items():
            hashes = pattern.findall(text)
            entities['hashes'][hash_type].update(hashes)
    
    def enrich_entities(self, entities: Dict) -> Dict:
        """
        Enrich entities with external data sources.
        
        Args:
            entities: Dictionary with extracted entities
            
        Returns:
            Dictionary with enriched data
        """
        self.logger.info("Enriching entities with external data")
        
        enriched = {
            'ips': {},
            'domains': {},
            'hashes': {},
            'enrichment_date': None
        }
        
        # Enrich IPs (placeholder for external API calls)
        for ip in entities.get('ips', [])[:100]:  # Limit for performance
            enriched['ips'][ip] = self._enrich_ip(ip)
        
        # Enrich domains (placeholder for external API calls)
        for domain in entities.get('domains', [])[:100]:  # Limit for performance
            enriched['domains'][domain] = self._enrich_domain(domain)
        
        # Enrich hashes (placeholder for external API calls)
        for hash_type in ['md5', 'sha1', 'sha256']:
            for hash_value in entities.get('hashes', {}).get(hash_type, [])[:50]:
                enriched['hashes'][hash_value] = self._enrich_hash(hash_value, hash_type)
        
        from datetime import datetime
        enriched['enrichment_date'] = datetime.now().isoformat()
        
        return enriched
    
    def _enrich_ip(self, ip: str) -> Dict:
        """
        Enrich IP address with external data.
        
        Args:
            ip: IP address
            
        Returns:
            Dictionary with enrichment data
        """
        # Placeholder for external enrichment (e.g., VirusTotal, AbuseIPDB, etc.)
        # This can be extended with actual API calls
        return {
            'ip': ip,
            'source': 'manual',
            'notes': 'External enrichment not implemented'
        }
    
    def _enrich_domain(self, domain: str) -> Dict:
        """
        Enrich domain with external data.
        
        Args:
            domain: Domain name
            
        Returns:
            Dictionary with enrichment data
        """
        # Placeholder for external enrichment (e.g., VirusTotal, etc.)
        return {
            'domain': domain,
            'source': 'manual',
            'notes': 'External enrichment not implemented'
        }
    
    def _enrich_hash(self, hash_value: str, hash_type: str) -> Dict:
        """
        Enrich hash with external data.
        
        Args:
            hash_value: Hash value
            hash_type: Type of hash (md5, sha1, sha256)
            
        Returns:
            Dictionary with enrichment data
        """
        # Placeholder for external enrichment (e.g., VirusTotal, etc.)
        return {
            'hash': hash_value,
            'type': hash_type,
            'source': 'manual',
            'notes': 'External enrichment not implemented'
        }
    
    def save_enriched_data(self, triage_dir: Path, enriched_data: Dict) -> Path:
        """
        Save enriched data to JSON file.
        
        Args:
            triage_dir: Path to triage output directory
            enriched_data: Enriched data dictionary
            
        Returns:
            Path to saved file
        """
        self.logger.info("Saving enriched data")
        
        enriched_file = triage_dir / "enriched.json"
        self.fs_utils.safe_write(enriched_file, json.dumps(enriched_data, indent=2))
        
        self.logger.info(f"Enriched data saved: {enriched_file}")
        return enriched_file
    
    def add_to_html_report(self, html_file: Path, enriched_data: Dict) -> Path:
        """
        Add enriched data to HTML report.
        
        Args:
            html_file: Path to HTML report
            enriched_data: Enriched data dictionary
            
        Returns:
            Path to updated HTML file
        """
        self.logger.info("Adding enriched data to HTML report")
        
        try:
            html_content = self.fs_utils.safe_read(html_file)
            if not html_content:
                return html_file
            
            # Find closing </div> before </body>
            enriched_section = self._build_enriched_section(enriched_data)
            
            # Insert before closing </div> of container
            html_content = html_content.replace('    </div>', f'{enriched_section}\n    </div>')
            
            self.fs_utils.safe_write(html_file, html_content)
            self.logger.info("Enriched data added to HTML report")
            
        except Exception as e:
            self.logger.exception(f"Error adding enriched data to HTML: {e}")
        
        return html_file
    
    def _build_enriched_section(self, enriched_data: Dict) -> str:
        """Build HTML section for enriched data."""
        html = """
        <h2>Enriched Context</h2>
        <div class="summary">
            <h3>Extracted Entities</h3>
"""
        
        # IPs
        ips = enriched_data.get('ips', {})
        if ips:
            html += f"<p><strong>IP Addresses:</strong> {len(ips)}</p><ul>"
            for ip in list(ips.keys())[:20]:  # Limit display
                html += f"<li>{ip}</li>"
            html += "</ul>"
        
        # Domains
        domains = enriched_data.get('domains', {})
        if domains:
            html += f"<p><strong>Domains:</strong> {len(domains)}</p><ul>"
            for domain in list(domains.keys())[:20]:  # Limit display
                html += f"<li>{domain}</li>"
            html += "</ul>"
        
        # Hashes
        hashes = enriched_data.get('hashes', {})
        if hashes:
            html += f"<p><strong>Hashes:</strong> {len(hashes)}</p><ul>"
            for hash_val in list(hashes.keys())[:20]:  # Limit display
                html += f"<li><code>{hash_val}</code></li>"
            html += "</ul>"
        
        html += "</div>"
        return html
    
    def enrich_triage(self, triage_dir: Path) -> Path:
        """
        Complete enrichment process for triage data.
        
        Args:
            triage_dir: Path to triage output directory
            
        Returns:
            Path to enriched data file
        """
        try:
            # Extract entities
            entities = self.extract_entities(triage_dir)
            
            # Enrich entities
            enriched_data = self.enrich_entities(entities)
            
            # Save enriched data
            enriched_file = self.save_enriched_data(triage_dir, enriched_data)
            
            # Add to HTML report if exists
            html_file = triage_dir / "report.html"
            if html_file.exists():
                self.add_to_html_report(html_file, enriched_data)
            
            return enriched_file
            
        except Exception as e:
            self.logger.exception(f"Error during enrichment: {e}")
            return None



