"""
Core DNS analyzer functionality.
Handles packet capture, DNS query analysis, and maliciousness scoring.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from scapy.all import sniff, DNS, DNSQR, IP
    from scapy.layers.dns import DNSRR
except ImportError:
    # Fallback for when scapy is not installed
    DNS = DNSQR = IP = DNSRR = None
    sniff = None

from utils.scoring import MaliciousnessScorer
from utils.data_handler import DataHandler


class DNSAnalyzer:
    """Main DNS analysis class."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the DNS analyzer with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.scorer = MaliciousnessScorer(config.get('scoring', {}))
        self.data_handler = DataHandler(config.get('data', {}))
        self.captured_packets = []
        self.analysis_results = []
        
    def start_analysis(self, interface: Optional[str] = None, output_file: str = "data/results.json") -> None:
        """Start DNS packet capture and analysis."""
        if not sniff:
            self.logger.error("Scapy not available. Please install requirements: pip install -r requirements.txt")
            return
            
        self.logger.info(f"Starting DNS analysis on interface: {interface or 'default'}")
        
        try:
            # Start packet capture
            sniff(
                iface=interface,
                filter="udp port 53",  # DNS traffic
                prn=self._process_packet,
                stop_filter=self._should_stop,
                timeout=self.config.get('capture_timeout', 60)
            )
            
            # Save results
            self._save_results(output_file)
            
        except Exception as e:
            self.logger.error(f"Error during packet capture: {e}")
            
    def _process_packet(self, packet) -> None:
        """Process a captured DNS packet."""
        if not packet.haslayer(DNS):
            return
            
        dns_layer = packet[DNS]
        
        # Extract DNS query information
        if dns_layer.qr == 0:  # Query
            self._process_dns_query(packet, dns_layer)
        else:  # Response
            self._process_dns_response(packet, dns_layer)
            
    def _process_dns_query(self, packet, dns_layer) -> None:
        """Process DNS query packet."""
        if dns_layer.qd:
            query_name = dns_layer.qd.qname.decode('utf-8').rstrip('.')
            
            query_info = {
                'timestamp': packet.time,
                'src_ip': packet[IP].src if packet.haslayer(IP) else 'unknown',
                'dst_ip': packet[IP].dst if packet.haslayer(IP) else 'unknown',
                'query_name': query_name,
                'query_type': dns_layer.qd.qtype,
                'type': 'query'
            }
            
            # Calculate maliciousness score
            score = self.scorer.calculate_score(query_info)
            query_info['maliciousness_score'] = score
            
            self.captured_packets.append(query_info)
            self.logger.debug(f"DNS Query: {query_name} (Score: {score})")
            
    def _process_dns_response(self, packet, dns_layer) -> None:
        """Process DNS response packet."""
        if dns_layer.an:
            for answer in dns_layer.an:
                if hasattr(answer, 'rdata'):
                    response_info = {
                        'timestamp': packet.time,
                        'src_ip': packet[IP].src if packet.haslayer(IP) else 'unknown',
                        'dst_ip': packet[IP].dst if packet.haslayer(IP) else 'unknown',
                        'response_name': answer.rrname.decode('utf-8').rstrip('.'),
                        'response_data': str(answer.rdata),
                        'ttl': answer.ttl,
                        'type': 'response'
                    }
                    
                    self.captured_packets.append(response_info)
                    
    def _should_stop(self, packet) -> bool:
        """Determine if packet capture should stop."""
        return len(self.captured_packets) >= self.config.get('max_packets', 1000)
        
    def _save_results(self, output_file: str) -> None:
        """Save analysis results to file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results = {
            'total_packets': len(self.captured_packets),
            'analysis_summary': self._generate_summary(),
            'packets': self.captured_packets
        }
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        self.logger.info(f"Results saved to {output_file}")
        
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary."""
        if not self.captured_packets:
            return {'message': 'No packets captured'}
            
        queries = [p for p in self.captured_packets if p.get('type') == 'query']
        high_risk = [p for p in queries if p.get('maliciousness_score', 0) > 0.7]
        
        return {
            'total_queries': len(queries),
            'high_risk_queries': len(high_risk),
            'risk_percentage': len(high_risk) / len(queries) * 100 if queries else 0,
            'top_domains': self._get_top_domains(queries)
        }
        
    def _get_top_domains(self, queries: List[Dict], limit: int = 10) -> List[str]:
        """Get most frequently queried domains."""
        domain_counts = {}
        for query in queries:
            domain = query.get('query_name', '')
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
        return sorted(domain_counts.keys(), key=lambda x: domain_counts[x], reverse=True)[:limit]