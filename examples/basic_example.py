#!/usr/bin/env python3
"""
Basic example demonstrating DNS analyzer functionality without requiring network capture.
This example shows how to use the scoring system and data handling components.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.scoring import MaliciousnessScorer
from utils.data_handler import DataHandler
from config.settings import get_default_config


def main():
    """Demonstrate basic functionality with sample data."""
    print("DNS Analyzer - Basic Example")
    print("=" * 40)
    
    # Initialize components
    config = get_default_config()
    scorer = MaliciousnessScorer(config.get('scoring', {}))
    data_handler = DataHandler(config.get('data', {}))
    
    # Sample DNS queries to analyze
    sample_queries = [
        {'query_name': 'google.com', 'src_ip': '192.168.1.100', 'timestamp': '2024-01-01T12:00:00'},
        {'query_name': 'facebook.com', 'src_ip': '192.168.1.100', 'timestamp': '2024-01-01T12:01:00'},
        {'query_name': 'malicious-domain.tk', 'src_ip': '192.168.1.101', 'timestamp': '2024-01-01T12:02:00'},
        {'query_name': 'very-long-suspicious-domain-name-that-might-be-generated.com', 'src_ip': '192.168.1.101', 'timestamp': '2024-01-01T12:03:00'},
        {'query_name': 'abc123xyz789.bit', 'src_ip': '192.168.1.102', 'timestamp': '2024-01-01T12:04:00'},
    ]
    
    print("Analyzing sample DNS queries...")
    print()
    
    scored_queries = []
    for query in sample_queries:
        score = scorer.calculate_score(query)
        query['maliciousness_score'] = score
        scored_queries.append(query)
        
        print(f"Domain: {query['query_name']}")
        print(f"Score: {score:.3f} {'(HIGH RISK)' if score > 0.7 else '(Low risk)' if score < 0.3 else '(Medium risk)'}")
        print()
    
    # Generate analysis results
    results = {
        'total_packets': len(scored_queries),
        'analysis_summary': {
            'total_queries': len(scored_queries),
            'high_risk_queries': len([q for q in scored_queries if q['maliciousness_score'] > 0.7]),
            'risk_percentage': len([q for q in scored_queries if q['maliciousness_score'] > 0.7]) / len(scored_queries) * 100,
            'top_domains': [q['query_name'] for q in scored_queries]
        },
        'packets': scored_queries
    }
    
    # Save results
    print("Saving results...")
    data_handler.save_analysis_results(results, 'example_analysis.json')
    data_handler.export_to_csv(scored_queries, 'example_queries.csv')
    data_handler.save_report(results, 'example_report.txt')
    
    # Display summary
    print("\nAnalysis Summary:")
    print(f"Total queries analyzed: {results['analysis_summary']['total_queries']}")
    print(f"High risk queries: {results['analysis_summary']['high_risk_queries']}")
    print(f"Risk percentage: {results['analysis_summary']['risk_percentage']:.1f}%")
    print()
    print("Files created in data/ directory:")
    print("- example_analysis.json (complete results)")
    print("- example_queries.csv (query data)")
    print("- example_report.txt (summary report)")
    print()
    print("Example completed successfully!")


if __name__ == "__main__":
    main()