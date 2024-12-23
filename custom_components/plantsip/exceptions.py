"""Exceptions for PlantSip."""

class PlantSipError(Exception):
    """Base exception for PlantSip."""

class PlantSipConnectionError(PlantSipError):
    """Error connecting to the PlantSip API."""

class PlantSipAuthError(PlantSipError):
    """Authentication error from the PlantSip API."""

class PlantSipApiError(PlantSipError):
    """Error response from the PlantSip API."""
