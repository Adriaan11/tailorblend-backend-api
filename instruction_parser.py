"""
Instruction Parser for TailorBlend AI Consultant

This module provides utilities to parse and reassemble the agent's
instructions, enabling granular editing of specific sections.
"""

import re
from collections import OrderedDict
from typing import Tuple


def parse_instructions(text: str) -> OrderedDict[str, str]:
    """
    Parse instructions text into sections based on markdown headers.

    Splits on `## N. SECTION NAME` markers to extract the 7 major sections:
    1. Core Identity & Role
    2. Natural Conversation Principles
    3. Value Proposition
    4. Interaction Workflow
    5. Technical Implementation
    6. Presenting the Blend
    7. Reminders & Best Practices

    Args:
        text: Full instructions text from instructions.txt

    Returns:
        OrderedDict mapping section names to their content

    Example:
        >>> sections = parse_instructions(instructions_text)
        >>> sections["1. CORE IDENTITY & ROLE"]
        "- **Company**: TAILORBLEND..."
    """

    # Split on ## N. pattern (major section headers)
    # Pattern captures the header line itself
    parts = re.split(r'(## \d+\. [^\n]+)', text)

    sections = OrderedDict()

    # parts[0] is the preamble (title before first ##)
    # parts[1] = "## 1. SECTION NAME"
    # parts[2] = content of section 1
    # parts[3] = "## 2. NEXT SECTION"
    # parts[4] = content of section 2
    # etc.

    # Store preamble if it exists (usually just "# TAILORBLEND AI CONSULTANT INSTRUCTIONS")
    if parts[0].strip():
        sections["_preamble"] = parts[0].strip()

    # Process pairs of (header, content)
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            header = parts[i].strip()
            content = parts[i + 1].strip()

            # Extract clean section name from header
            # "## 1. CORE IDENTITY & ROLE" -> "1. CORE IDENTITY & ROLE"
            section_name = header.replace("##", "").strip()

            sections[section_name] = content

    return sections


def reassemble_instructions(sections: OrderedDict[str, str]) -> str:
    """
    Reassemble sections back into full instructions text.

    Args:
        sections: OrderedDict of section names to content

    Returns:
        Full instructions text ready for agent

    Example:
        >>> sections["2. NATURAL CONVERSATION PRINCIPLES"] = "Updated content..."
        >>> full_text = reassemble_instructions(sections)
    """

    parts = []

    # Add preamble if it exists
    if "_preamble" in sections:
        parts.append(sections["_preamble"])
        parts.append("")  # Blank line after preamble

    # Add each section with its header
    for section_name, content in sections.items():
        if section_name == "_preamble":
            continue  # Already added

        # Reconstruct header: "1. SECTION NAME" -> "## 1. SECTION NAME"
        header = f"## {section_name}"
        parts.append(header)
        parts.append(content)
        parts.append("")  # Blank line after each section

    # Join with newlines
    return "\n".join(parts).strip() + "\n"


def get_section_line_count(content: str) -> int:
    """
    Calculate appropriate number of lines for a textbox based on content.

    Args:
        content: Section content text

    Returns:
        Recommended number of lines for Gradio textbox

    Example:
        >>> lines = get_section_line_count(section_content)
        >>> gr.Textbox(lines=lines, ...)
    """

    # Count actual newlines
    line_count = content.count("\n") + 1

    # Add some padding for comfortable editing
    padded_count = int(line_count * 1.2)

    # Clamp between 5 and 35 lines
    return max(5, min(35, padded_count))


def validate_instructions(text: str) -> Tuple[bool, str]:
    """
    Validate that instructions text has required structure.

    Args:
        text: Instructions text to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if structure is valid
        - error_message: Empty string if valid, error description otherwise

    Example:
        >>> valid, error = validate_instructions(edited_text)
        >>> if not valid:
        ...     print(f"Error: {error}")
    """

    # Check minimum length (should be at least 1000 characters)
    if len(text.strip()) < 1000:
        return False, "Instructions are too short (minimum 1000 characters)"

    # Check for required sections
    required_sections = [
        "CORE IDENTITY",
        "CONVERSATION",
        "VALUE PROPOSITION",
        "WORKFLOW",
        "TECHNICAL",
    ]

    missing_sections = []
    for section in required_sections:
        if section.lower() not in text.lower():
            missing_sections.append(section)

    if missing_sections:
        return False, f"Missing required sections: {', '.join(missing_sections)}"

    # All checks passed
    return True, ""
