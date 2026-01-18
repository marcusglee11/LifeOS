import yaml
from pathlib import Path

def load_config(config_path: Path) -> dict:
    """
    Load and structurally validate a YAML config file.
    
    Args:
        config_path: Path to the YAML file
        
    Returns:
        Validated config as dict
        
    Raises:
        ValueError: If file is missing, malformed, or fails structural validation
    """
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML in {config_path}: {e}")
    
    # Layer 1 Structural Validation
    if data is None:
        # Empty file is valid but must be returned as dict
        return {}
        
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping (dict), found {type(data).__name__}")
        
    for key in data.keys():
        if not isinstance(key, str):
            raise ValueError(f"Config keys must be strings, found {type(key).__name__}: {key}")
            
    return data
