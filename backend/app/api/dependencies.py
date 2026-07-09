"""FastAPI dependency injection functions.

Provides reusable, type-annotated dependencies for route handlers,
including validated settings and shared service instances.
"""

from typing import Annotated

from fastapi import Depends

from app.config import Settings, settings


def get_settings() -> Settings:
    """Return the application settings singleton.

    Returns:
        The global Settings instance loaded from environment variables.
    """
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
