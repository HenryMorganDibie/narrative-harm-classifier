"""
core/yaml_loader.py — Shared "check path exists, open, yaml.safe_load" helper.

Previously duplicated across classifier/taxonomy/loader.py,
classifier/validators/benchmark.py, and classifier/rules/patterns_loader.py.
"""

from pathlib import Path
from typing import Union

import yaml


def load_yaml_file(path: Union[str, Path]) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML config not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
