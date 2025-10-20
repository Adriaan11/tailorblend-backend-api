"""
Shared Database Loader

Loads ingredient and base mix databases from JSON files and formats them
for agent context. Uses module-level caching to load files once at startup.

This module provides:
- load_ingredients_database() - 111 ingredients with dosages and constraints
- load_base_mixes_database() - 4 base mixes with customization options
- get_combined_database() - Both databases formatted for agent context
"""

import json
from pathlib import Path
from typing import Optional
import aiofiles

# Module-level cache (loaded once at import time)
_CACHED_INGREDIENTS: Optional[str] = None
_CACHED_BASE_MIXES: Optional[str] = None


def _get_spec_path(filename: str) -> Path:
    """Get absolute path to a file in the spec/ directory."""
    project_root = Path(__file__).parent.parent
    return project_root / "spec" / filename


async def load_ingredients_database() -> str:
    """
    Load and format the ingredients database (Ingredients3.json).

    Returns a formatted string containing all 111 ingredients with:
    - Name
    - Dosage ranges (minimum, recommended, maximum)
    - Cost per 30 servings (ZAR)
    - Special notes/constraints

    Results are cached at module level for performance.

    Returns:
        str: Formatted ingredient database ready for agent context
    """
    global _CACHED_INGREDIENTS

    # Return cached version if available
    if _CACHED_INGREDIENTS is not None:
        return _CACHED_INGREDIENTS

    # Load and format
    ingredients_file = _get_spec_path("Ingredients3.json")

    async with aiofiles.open(ingredients_file, 'r', encoding='utf-8') as f:
        content = await f.read()
        ingredients = json.loads(content)

    # Format ingredients as readable text for agent
    formatted_lines = [
        "=" * 80,
        "INGREDIENTS DATABASE (111 Available Ingredients)",
        "=" * 80,
        ""
    ]

    for ing in ingredients:
        # Get fields with safe fallbacks for different JSON schema versions
        ing_id = ing.get('ingredientId', 'N/A')
        name = ing.get('name', 'Unknown')
        min_range = ing.get('minimumRange', ing.get('minimumrange', 'N/A'))
        rec_range = ing.get('reccomendedRange', ing.get('reccomendedrange', 'N/A'))
        max_range = ing.get('customerMaxRange', ing.get('customermaxrange', 'N/A'))
        unit = ing.get('unitOfMeasureName', ing.get('unitofmeasurename', 'units'))
        cost = ing.get('pricePer30Servings', ing.get('priceper30servings', '0.00'))
        overview = ing.get('overview', '')

        formatted_lines.append(f"• {name} (ID: {ing_id})")
        formatted_lines.append(f"  Dosage Range: {min_range} - {rec_range} {unit} (Max: {max_range} {unit})")
        formatted_lines.append(f"  Cost: R{cost} per 30 servings")
        if overview:
            formatted_lines.append(f"  Notes: {overview}")
        formatted_lines.append("")  # Blank line between ingredients

    _CACHED_INGREDIENTS = "\n".join(formatted_lines)
    return _CACHED_INGREDIENTS


async def load_base_mixes_database() -> str:
    """
    Load and format the base mixes database (BaseAddMixes2.json).

    Returns a formatted string containing:
    - 4 base mix types (Shake Whey, Shake Vegan, Drink, Capsules)
    - 68 customization options grouped by type
    - Default selections marked

    Results are cached at module level for performance.

    Returns:
        str: Formatted base mixes database ready for agent context
    """
    global _CACHED_BASE_MIXES

    # Return cached version if available
    if _CACHED_BASE_MIXES is not None:
        return _CACHED_BASE_MIXES

    # Load and format
    base_mixes_file = _get_spec_path("BaseAddMixes2.json")

    async with aiofiles.open(base_mixes_file, 'r', encoding='utf-8') as f:
        content = await f.read()
        base_mixes = json.loads(content)

    # Group by baseMixId for clearer presentation
    base_mix_groups = {}
    for item in base_mixes:
        base_id = item['baseMixId']
        if base_id not in base_mix_groups:
            base_mix_groups[base_id] = {
                'name': item['baseMixName'],
                'options': {}
            }

        add_type = item['addMixTypeName']
        if add_type not in base_mix_groups[base_id]['options']:
            base_mix_groups[base_id]['options'][add_type] = []

        base_mix_groups[base_id]['options'][add_type].append({
            'id': item['addMixId'],
            'name': item['addMixName'],
            'default': item['defaultFlag']
        })

    # Format as readable text
    formatted_lines = [
        "",
        "=" * 80,
        "BASE MIX & CUSTOMIZATION OPTIONS (4 Base Types, 68 Options)",
        "=" * 80,
        ""
    ]

    for base_id, base_info in sorted(base_mix_groups.items()):
        formatted_lines.append(f"\n{'*' * 80}")
        formatted_lines.append(f"BASE MIX (ID: {base_id}): {base_info['name']}")
        formatted_lines.append(f"{'*' * 80}")

        for add_type, options in sorted(base_info['options'].items()):
            formatted_lines.append(f"\n  {add_type} Options:")
            for opt in options:
                default_marker = " [DEFAULT]" if opt['default'] else ""
                formatted_lines.append(f"    - Add-Mix ID {opt['id']}: {opt['name']}{default_marker}")

        formatted_lines.append("")  # Blank line between base mixes

    _CACHED_BASE_MIXES = "\n".join(formatted_lines)
    return _CACHED_BASE_MIXES


async def get_combined_database() -> str:
    """
    Get both ingredients and base mixes databases combined.

    This is the primary function for agents that need access to
    the complete TailorBlend product catalog.

    Returns:
        str: Complete formatted database (ingredients + base mixes)
    """
    ingredients = await load_ingredients_database()
    base_mixes = await load_base_mixes_database()

    return f"{ingredients}\n{base_mixes}"


def clear_cache() -> None:
    """
    Clear the module-level cache.

    Useful for testing or if database files are updated at runtime.
    """
    global _CACHED_INGREDIENTS, _CACHED_BASE_MIXES
    _CACHED_INGREDIENTS = None
    _CACHED_BASE_MIXES = None
