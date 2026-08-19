"""dotconfig - Create config objects from JSON/YAML"""

import json
from pathlib import Path

import yaml


class Config:
    """Wrapper for nested config with dot-notation access.

    >>> config = Config({"database": {"host": "localhost", "port": 5432}})
    >>> config.database.host
    'localhost'
    >>> config.database.port
    5432

    Supports loading JSON/YAML
    """

    def __new__(cls, config):
        if isinstance(config, list):
            return [cls(c) if isinstance(c, (list, dict)) else c for c in config]
        return super().__new__(cls)

    def __init__(self, config: dict):
        self._config = config

    @classmethod
    def from_json(cls, file):
        """Load from JSON file"""
        data = cls._get_data(file, json.load)
        return cls(data)

    @classmethod
    def from_yaml(cls, file):
        """Load from YAML file"""
        data = cls._get_data(file, yaml.safe_load)
        return cls(data)

    @staticmethod
    def _get_data(source, loader):
        """Load data from file object or path"""
        try:
            filepath = Path(source)
        except TypeError:
            # treat as filelike
            data = loader(source)
        else:
            with open(filepath) as f:
                data = loader(f)
        return data

    def __getattr__(self, name):
        try:
            value = self._config[name]
        except KeyError as e:
            raise AttributeError(f"No config '{name}' found.") from e

        if isinstance(value, (dict, list)):
            return Config(value)
        return value

    def __getitem__(self, name):
        value = self._config[name]
        if isinstance(value, (list, dict)):
            return Config(value)
        return value

    def __str__(self):
        return json.dumps(self._config)

    def __repr__(self):
        cls_name = type(self).__name__
        return f"{cls_name}({self._config!r})"
