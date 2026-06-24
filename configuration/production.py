from __future__ import annotations

from .base import BaseConfig


class ProductionConfig(BaseConfig):
    DEBUG = False
