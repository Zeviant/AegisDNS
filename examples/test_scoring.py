#!/usr/bin/env python3
"""
Test the scoring system without requiring external dependencies.
This demonstrates the core maliciousness scoring functionality.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.scoring import MaliciousnessScorer
from config.settings import get_default_config


def main():
    """Test the scoring system with various domain examples."""
    print("DNS Maliciousness Scorer - Test Example")
    print("=" * 50)
    
    # Initialize scorer
    config = get_default_config()
    scorer = MaliciousnessScorer(config.get('scoring', {}))
    
    # Test domains with expected behaviors
    test_domains = [
        # Legitimate domains (should score 0.0)
        ('google.com', 'Legitimate - Popular search engine'),
        ('github.com', 'Legitimate - Code repository'),
        ('stackoverflow.com', 'Legitimate - Developer Q&A'),
        
        # Suspicious domains (should score > 0)
        ('malicious.tk', 'Suspicious - .tk TLD'),
        ('random123456789.ml', 'Suspicious - .ml TLD with numbers'),
        ('very-long-domain-name-that-might-be-generated-algorithmically.com', 'Suspicious - Very long'),
        ('abc123def456ghi789.bit', 'Suspicious - .bit TLD with mixed alphanumeric'),
        ('short.tk', 'Suspicious - .tk TLD'),
        ('x' * 60 + '.com', 'Suspicious - Extremely long domain'),
        
        # Test entropy detection
        ('randomstringwithveryhighentropy.com', 'High entropy test'),
        ('aaaaaaaaaaaaaaaaaaaaaa.com', 'Low entropy test'),
    ]
    
    print("Testing domains against maliciousness scoring system:\n")
    
    results = []
    for domain, description in test_domains:
        score = scorer.calculate_score({'query_name': domain})
        risk_level = 'HIGH' if score > 0.7 else 'MEDIUM' if score > 0.3 else 'LOW'
        
        results.append((domain, score, risk_level, description))
        
        print(f"Domain: {domain}")
        print(f"Description: {description}")
        print(f"Score: {score:.3f} (Risk Level: {risk_level})")
        print("-" * 50)
    
    # Summary statistics
    high_risk = len([r for r in results if r[2] == 'HIGH'])
    medium_risk = len([r for r in results if r[2] == 'MEDIUM'])
    low_risk = len([r for r in results if r[2] == 'LOW'])
    
    print(f"\nSummary Statistics:")
    print(f"Total domains tested: {len(results)}")
    print(f"High risk: {high_risk}")
    print(f"Medium risk: {medium_risk}")
    print(f"Low risk: {low_risk}")
    
    # Test entropy calculation directly
    print(f"\nEntropy Analysis Examples:")
    random_string = "abcdefghijklmnop"
    repetitive_string = "aaaaaaaaaaaaaaaa"
    
    random_entropy = scorer._calculate_entropy(random_string)
    repetitive_entropy = scorer._calculate_entropy(repetitive_string)
    
    print(f"Random string '{random_string}' entropy: {random_entropy:.3f}")
    print(f"Repetitive string '{repetitive_string}' entropy: {repetitive_entropy:.3f}")
    
    print("\nScoring system test completed successfully!")


if __name__ == "__main__":
    main()