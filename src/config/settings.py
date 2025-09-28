"""
Configuration management for the DNS analyzer.
Handles loading and validation of configuration files.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        logging.warning(f"Config file not found: {config_path}, using defaults")
        return get_default_config()
        
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Get default configuration."""
    return {
        'capture_timeout': 300,  # 5 minutes
        'max_packets': 10000,
        'scoring': {
            'enable_pattern_matching': True,
            'enable_entropy_analysis': True,
            'suspicious_threshold': 0.7
        },
        'data': {
            'data_directory': 'data',
            'enable_csv_export': True,
            'enable_reports': True
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/dns_analyzer.log',
            'max_size_mb': 10,
            'backup_count': 5
        },
        'network': {
            'dns_port': 53,
            'capture_filter': 'udp port 53',
            'promiscuous_mode': False
        }
    }


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration parameters."""
    required_keys = ['capture_timeout', 'max_packets']
    
    for key in required_keys:
        if key not in config:
            logging.error(f"Missing required config key: {key}")
            return False
            
    return True