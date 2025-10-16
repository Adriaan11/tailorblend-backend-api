"""
TailorBlend Configuration Package

This package handles configuration management for the TailorBlend AI Consultant.
"""

from .settings import (
    load_instructions,
    OPENAI_API_KEY,
    VECTOR_STORE_ID,
    MAX_CONVERSATION_TURNS,
)

__all__ = [
    "load_instructions",
    "OPENAI_API_KEY",
    "VECTOR_STORE_ID",
    "MAX_CONVERSATION_TURNS",
]
