"""
Configuration and Prompt Management

This module handles loading the system prompt from instructions.txt
and managing environment configuration.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SPEC_DIR = PROJECT_ROOT / "spec"
INSTRUCTIONS_FILE = SPEC_DIR / "instructions.txt"
PRACTITIONER_INSTRUCTIONS_FILE = SPEC_DIR / "practitioner-instructions.txt"


def load_instructions() -> str:
    """
    Load instructions.txt as the system prompt for the agent.

    This file contains all business logic, conversation flow,
    and domain expertise for the TailorBlend consultant.

    Returns:
        str: Full instructions text to be used as agent instructions

    Raises:
        FileNotFoundError: If instructions.txt doesn't exist
    """
    if not INSTRUCTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Instructions file not found at {INSTRUCTIONS_FILE}. "
            f"Please ensure spec/instructions.txt exists."
        )

    with open(INSTRUCTIONS_FILE, 'r', encoding='utf-8') as f:
        instructions = f.read()

    # Validate it's not empty
    if not instructions.strip():
        raise ValueError("Instructions file is empty!")

    return instructions


def load_practitioner_instructions() -> str:
    """
    Load practitioner-instructions.txt as the system prompt for practitioner mode.

    This file contains clinical-grade instructions for healthcare practitioners,
    including comprehensive drug interaction analysis, evidence-based rationale,
    and professional formulation guidance.

    Returns:
        str: Full practitioner instructions text to be used as agent instructions

    Raises:
        FileNotFoundError: If practitioner-instructions.txt doesn't exist
    """
    if not PRACTITIONER_INSTRUCTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Practitioner instructions file not found at {PRACTITIONER_INSTRUCTIONS_FILE}. "
            f"Please ensure spec/practitioner-instructions.txt exists."
        )

    with open(PRACTITIONER_INSTRUCTIONS_FILE, 'r', encoding='utf-8') as f:
        instructions = f.read()

    # Validate it's not empty
    if not instructions.strip():
        raise ValueError("Practitioner instructions file is empty!")

    return instructions


# OpenAI Configuration
# Load from environment variable (required)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY not found in environment. "
        "Please set it in .env file or environment variables."
    )

# Vector Store Configuration
# This vector store contains:
# - ingredients-database.md (111 ingredients with dosages, constraints, categories)
# - base-add-mixes-database.md (4 base mixes, 68 customization options)
VECTOR_STORE_ID = "vs_68ee8e3a25a48191aa18ff9c1dddbc01"

# Conversation Configuration
MAX_CONVERSATION_TURNS = 50  # Allow full consultation with plenty of back-and-forth
