"""
Configuration loader for BrainWaves Project.

Reads `config/settings.yaml` and returns a nested dict of all settings
(Emotiv credentials, EEG parameters, mood thresholds, Temi config, etc.).
"""

import os
import yaml


def load_config(config_path=None):
    """Load project settings from a YAML config file.

    Args:
        config_path: Path to settings.yaml. Defaults to
            <repo_root>/config/settings.yaml.

    Returns:
        dict: Parsed YAML configuration.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "settings.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)
