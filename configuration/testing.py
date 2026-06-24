from __future__ import annotations

from .base import BaseConfig


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
