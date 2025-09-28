"""
Maliciousness scoring system for DNS queries.
Implements various heuristics to score the likelihood of malicious activity.
"""

import re
from typing import Dict, List, Any
import logging


class MaliciousnessScorer:
    """Calculate maliciousness scores for DNS queries."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize scorer with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Known malicious patterns (simplified for demo)
        self.suspicious_patterns = [
            r'.*\.tk$',              # .tk domains often used maliciously
            r'.*\.ml$',              # .ml domains
            r'[0-9]{8,}',            # Long numeric sequences
            r'[a-z]{20,}',           # Very long random strings
            r'.*bit\.ly.*',          # URL shorteners
            r'.*tinyurl.*',
            r'.*\.bit$',             # Alternative DNS
        ]
        
        # Known legitimate domains (whitelist)
        self.legitimate_domains = [
            'google.com', 'youtube.com', 'facebook.com', 'amazon.com',
            'microsoft.com', 'apple.com', 'netflix.com', 'github.com',
            'stackoverflow.com', 'wikipedia.org'
        ]
        
    def calculate_score(self, query_info: Dict[str, Any]) -> float:
        """Calculate maliciousness score for a DNS query."""
        domain = query_info.get('query_name', '').lower()
        score = 0.0
        
        # Check against whitelist first
        if self._is_legitimate(domain):
            return 0.0
            
        # Pattern-based scoring
        score += self._check_suspicious_patterns(domain)
        
        # Domain characteristics scoring
        score += self._check_domain_characteristics(domain)
        
        # Frequency-based scoring (if available)
        score += self._check_frequency_anomalies(query_info)
        
        # Normalize score to 0-1 range
        return min(score, 1.0)
        
    def _is_legitimate(self, domain: str) -> bool:
        """Check if domain is in legitimate whitelist."""
        for legitimate in self.legitimate_domains:
            if domain.endswith(legitimate):
                return True
        return False
        
    def _check_suspicious_patterns(self, domain: str) -> float:
        """Check domain against suspicious patterns."""
        score = 0.0
        
        for pattern in self.suspicious_patterns:
            if re.match(pattern, domain):
                score += 0.3
                self.logger.debug(f"Suspicious pattern match: {pattern} for {domain}")
                
        return score
        
    def _check_domain_characteristics(self, domain: str) -> float:
        """Score based on domain characteristics."""
        score = 0.0
        
        # Very long domains are suspicious
        if len(domain) > 50:
            score += 0.2
            
        # Domains with many subdomains
        subdomain_count = domain.count('.')
        if subdomain_count > 4:
            score += 0.15
            
        # High entropy (randomness) in domain name
        entropy = self._calculate_entropy(domain)
        if entropy > 4.0:  # High entropy threshold
            score += 0.2
            
        # Suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.bit']
        if any(domain.endswith(tld) for tld in suspicious_tlds):
            score += 0.25
            
        return score
        
    def _check_frequency_anomalies(self, query_info: Dict[str, Any]) -> float:
        """Check for frequency-based anomalies."""
        # This would typically involve checking against historical data
        # For now, return a placeholder score
        return 0.0
        
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        import math
        
        if not text:
            return 0.0
            
        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
            
        # Calculate entropy
        entropy = 0.0
        text_len = len(text)
        
        for count in char_counts.values():
            probability = count / text_len
            entropy -= probability * math.log2(probability)
            
        return entropy