"""
Data handling utilities for DNS analysis results.
Manages data storage, retrieval, and export functionality.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class DataHandler:
    """Handle data storage and retrieval for DNS analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize data handler with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(config.get('data_directory', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def save_analysis_results(self, results: Dict[str, Any], filename: str) -> None:
        """Save analysis results to JSON file."""
        filepath = self.data_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            self.logger.info(f"Analysis results saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            
    def load_analysis_results(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load analysis results from JSON file."""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            self.logger.warning(f"File not found: {filepath}")
            return None
            
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading results: {e}")
            return None
            
    def export_to_csv(self, data: List[Dict[str, Any]], filename: str) -> None:
        """Export data to CSV file."""
        filepath = self.data_dir / filename
        
        if not data:
            self.logger.warning("No data to export")
            return
            
        try:
            if PANDAS_AVAILABLE:
                # Use pandas if available
                import pandas as pd
                df = pd.DataFrame(data)
                df.to_csv(filepath, index=False)
            else:
                # Fallback to basic CSV writing
                if data:
                    fieldnames = data[0].keys()
                    with open(filepath, 'w', newline='') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data)
            self.logger.info(f"Data exported to CSV: {filepath}")
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a text report from analysis results."""
        report_lines = []
        report_lines.append("DNS Analysis Report")
        report_lines.append("=" * 50)
        report_lines.append("")
        
        summary = results.get('analysis_summary', {})
        
        report_lines.append(f"Total Packets Analyzed: {results.get('total_packets', 0)}")
        report_lines.append(f"Total DNS Queries: {summary.get('total_queries', 0)}")
        report_lines.append(f"High Risk Queries: {summary.get('high_risk_queries', 0)}")
        report_lines.append(f"Risk Percentage: {summary.get('risk_percentage', 0):.2f}%")
        report_lines.append("")
        
        top_domains = summary.get('top_domains', [])
        if top_domains:
            report_lines.append("Top Queried Domains:")
            report_lines.append("-" * 20)
            for i, domain in enumerate(top_domains[:10], 1):
                report_lines.append(f"{i}. {domain}")
            report_lines.append("")
            
        return "\n".join(report_lines)
        
    def save_report(self, results: Dict[str, Any], filename: str) -> None:
        """Save analysis report to text file."""
        report = self.generate_report(results)
        filepath = self.data_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                f.write(report)
            self.logger.info(f"Report saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
            
    def get_historical_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Retrieve historical analysis data for comparison."""
        # This would typically query a database or file system
        # For now, return empty list as placeholder
        self.logger.info(f"Retrieving historical data for {days} days")
        return []