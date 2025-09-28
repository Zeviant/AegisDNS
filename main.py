#!/usr/bin/env python3
"""
DNS Level Connection Interception, Analysis, and Maliciousness Scoring System
Main entry point for the Capstone project.

Authors: [Add your names here]
Date: 2024
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dns_analyzer.core import DNSAnalyzer
from config.settings import load_config


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/dns_analyzer.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Main function to run the DNS analyzer."""
    parser = argparse.ArgumentParser(
        description="DNS Level Connection Interception, Analysis, and Maliciousness Scoring System"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="src/config/default.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--interface",
        type=str,
        help="Network interface to monitor (optional)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/analysis_results.json",
        help="Output file for analysis results",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = load_config(args.config)
        logger.info("Configuration loaded successfully")

        # Initialize DNS analyzer
        analyzer = DNSAnalyzer(config)
        logger.info("DNS Analyzer initialized")

        # Start analysis
        logger.info("Starting DNS analysis...")
        analyzer.start_analysis(
            interface=args.interface,
            output_file=args.output
        )

    except KeyboardInterrupt:
        logger.info("Analysis stopped by user")
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()