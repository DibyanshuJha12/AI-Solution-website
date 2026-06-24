from __future__ import annotations

from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    EXPOSE_RESET_LINKS_IN_DEBUG = True
