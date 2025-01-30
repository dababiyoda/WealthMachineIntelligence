"""
Configuration management for the WealthMachineOntology Framework
Uses JSON for configuration (will migrate to YAML when dependencies are resolved)
"""
import json
import os
from typing import Any, Dict, Optional

class ConfigManager:
    """Manages configuration for the framework"""
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._config_path = "config"

    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        config_file = os.path.join(self._config_path, f"{config_name}.json")
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def get_value(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value by key"""
        return self._config.get(key, default)

    def set_value(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self._config[key] = value

config_manager = ConfigManager()
