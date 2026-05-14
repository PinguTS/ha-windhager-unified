"""Windhager integration typed exceptions."""

from __future__ import annotations


class WindhagerError(Exception):
    """Base exception for all Windhager errors."""


class WindhagerAuthError(WindhagerError):
    """Authentication failed (HTTP 401)."""


class WindhagerApiError(WindhagerError):
    """API returned an error response."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class WindhagerTimeoutError(WindhagerError):
    """Request timed out."""


class WindhagerConnectionError(WindhagerError):
    """Network connection failed."""
