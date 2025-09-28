"""
Test cases for the maliciousness scoring system.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.scoring import MaliciousnessScorer


class TestMaliciousnessScorer:
    """Test cases for MaliciousnessScorer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {'suspicious_threshold': 0.7}
        self.scorer = MaliciousnessScorer(self.config)
        
    def test_legitimate_domain_score(self):
        """Test that legitimate domains get low scores."""
        query_info = {'query_name': 'google.com'}
        score = self.scorer.calculate_score(query_info)
        assert score == 0.0, "Legitimate domain should have score of 0"
        
    def test_suspicious_pattern_detection(self):
        """Test detection of suspicious patterns."""
        query_info = {'query_name': 'malicious.tk'}
        score = self.scorer.calculate_score(query_info)
        assert score > 0, "Suspicious domain should have positive score"
        
    def test_long_domain_scoring(self):
        """Test scoring of very long domains."""
        long_domain = 'a' * 60 + '.com'
        query_info = {'query_name': long_domain}
        score = self.scorer.calculate_score(query_info)
        assert score > 0, "Very long domain should have positive score"
        
    def test_entropy_calculation(self):
        """Test entropy calculation."""
        # High entropy (random) string
        high_entropy = self.scorer._calculate_entropy('abcdefghijklmnop')
        # Low entropy (repetitive) string
        low_entropy = self.scorer._calculate_entropy('aaaaaaaaaaaaaaaa')
        
        assert high_entropy > low_entropy, "Random string should have higher entropy"
        
    def test_score_normalization(self):
        """Test that scores are normalized to 0-1 range."""
        # Create a highly suspicious domain
        query_info = {'query_name': 'x' * 100 + '.tk'}
        score = self.scorer.calculate_score(query_info)
        assert 0 <= score <= 1, "Score should be normalized to 0-1 range"