"""
Test cases for configuration management.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import load_config, get_default_config, validate_config


class TestConfigManagement:
    """Test cases for configuration management."""
    
    def test_default_config(self):
        """Test that default configuration is valid."""
        config = get_default_config()
        assert validate_config(config), "Default config should be valid"
        assert 'capture_timeout' in config
        assert 'max_packets' in config
        
    def test_load_nonexistent_config(self):
        """Test loading non-existent config file returns defaults."""
        config = load_config('nonexistent.yaml')
        default_config = get_default_config()
        assert config == default_config
        
    def test_load_valid_config(self):
        """Test loading a valid config file."""
        test_config = {
            'capture_timeout': 120,
            'max_packets': 5000,
            'scoring': {'suspicious_threshold': 0.5}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name
            
        try:
            loaded_config = load_config(temp_path)
            assert loaded_config['capture_timeout'] == 120
            assert loaded_config['max_packets'] == 5000
        finally:
            Path(temp_path).unlink()
            
    def test_config_validation(self):
        """Test configuration validation."""
        valid_config = {'capture_timeout': 300, 'max_packets': 1000}
        invalid_config = {'capture_timeout': 300}  # missing max_packets
        
        assert validate_config(valid_config) is True
        assert validate_config(invalid_config) is False