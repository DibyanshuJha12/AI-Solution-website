from __future__ import annotations

import os

from .env import load_env_file

load_env_file()

from .base import BaseConfig
from .development import DevelopmentConfig
from .production import ProductionConfig
from .testing import TestingConfig


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config_class() -> type[BaseConfig]:
    environment = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).strip().lower()
    return CONFIG_MAP.get(environment, DevelopmentConfig)


Config = get_config_class()

__all__ = [
    "BaseConfig",
    "Config",
    "DevelopmentConfig",
    "ProductionConfig",
    "TestingConfig",
    "get_config_class",
    "load_env_file",
]
