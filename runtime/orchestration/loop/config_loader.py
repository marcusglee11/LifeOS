"""
PolicyConfigLoader - Load policy config for ConfigurableLoopPolicy.

Loads and validates YAML policy config with:
- Budgets (retry limits)
- Failure routing (default action, terminal outcomes)
- Waiver rules
- Progress detection
- Determinism settings
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class PolicyConfigLoadError(Exception):
    """Raised when policy config load fails."""
    pass


class PolicyConfigLoader:
    """Loads policy configuration from YAML file."""
    
    def __init__(self, config_path: Path):
        """
        Initialize loader with config file path.
        
        Args:
            config_path: Path to YAML config file
        """
        self.config_path = Path(config_path)
    
    def load(self) -> Dict[str, Any]:
        """
        Load and parse policy config.
        
        Returns:
            Parsed config dict
            
        Raises:
            PolicyConfigLoadError: On any load failure
        """
        if not self.config_path.exists():
            raise PolicyConfigLoadError(f"Config file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PolicyConfigLoadError(f"YAML parse error: {e}")
        except Exception as e:
            raise PolicyConfigLoadError(f"Failed to load config: {e}")
        
        if not isinstance(config, dict):
            raise PolicyConfigLoadError("Config must be a dictionary")
        
        # Validate required sections
        required_sections = ["budgets", "failure_routing"]
        for section in required_sections:
            if section not in config:
                raise PolicyConfigLoadError(f"Missing required section: {section}")
        
        return config
