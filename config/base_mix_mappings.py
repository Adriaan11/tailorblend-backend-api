"""
Base Mix Type ID Mappings

Maps baseMixId → baseMixTypeId for production API compatibility.

The production API requires both baseMixId and baseMixTypeId when creating blends.
BaseMixId comes from our database (BaseAddMixes2.json), but baseMixTypeId is a
separate system identifier used by the production backend.

Based on request.json example:
- baseMixId: 2 (Drink) → baseMixTypeId: 54 (CONFIRMED)

Other mappings are educated guesses based on sequential IDs and need verification:
- baseMixId: 1 (Shake Whey) → baseMixTypeId: 51 (TODO: VERIFY)
- baseMixId: 6 (Nutriblend-F) → baseMixTypeId: 52 (TODO: VERIFY)
- baseMixId: 8 (Shake Vegan) → baseMixTypeId: 53 (TODO: VERIFY)

TODO: Test with production API and update if these fail validation.
"""

# Hard-coded mapping: baseMixId → metadata including baseMixTypeId
BASE_MIX_TYPE_MAPPING = {
    1: {
        "name": "Shake (Whey)",
        "typeId": 51,  # TODO: VERIFY - Guessed based on sequential pattern
        "description": "Whey protein shake base"
    },
    2: {
        "name": "Drink",
        "typeId": 54,  # ✅ CONFIRMED from request.json
        "description": "Powder drink mix base"
    },
    6: {
        "name": "Nutriblend - F",
        "typeId": 52,  # TODO: VERIFY - Guessed based on sequential pattern
        "description": "Nutriblend formulation base"
    },
    8: {
        "name": "Shake (Vegan)",
        "typeId": 53,  # TODO: VERIFY - Guessed based on sequential pattern
        "description": "Plant-based protein shake base"
    }
}


def get_base_mix_type_id(base_mix_id: int) -> int:
    """
    Get baseMixTypeId for given baseMixId.

    Args:
        base_mix_id: The base mix ID from our database (1, 2, 6, or 8)

    Returns:
        The corresponding baseMixTypeId required by production API

    Raises:
        ValueError: If base_mix_id is not recognized

    Example:
        >>> get_base_mix_type_id(2)  # Drink
        54
    """
    mapping = BASE_MIX_TYPE_MAPPING.get(base_mix_id)
    if not mapping:
        raise ValueError(
            f"Unknown baseMixId: {base_mix_id}. "
            f"Valid IDs: {list(BASE_MIX_TYPE_MAPPING.keys())}"
        )
    return mapping["typeId"]


def get_base_mix_info(base_mix_id: int) -> dict:
    """
    Get complete base mix information including name and typeId.

    Args:
        base_mix_id: The base mix ID from our database

    Returns:
        Dict with 'name', 'typeId', and 'description'

    Example:
        >>> get_base_mix_info(2)
        {'name': 'Drink', 'typeId': 54, 'description': '...'}
    """
    mapping = BASE_MIX_TYPE_MAPPING.get(base_mix_id)
    if not mapping:
        raise ValueError(
            f"Unknown baseMixId: {base_mix_id}. "
            f"Valid IDs: {list(BASE_MIX_TYPE_MAPPING.keys())}"
        )
    return mapping.copy()


def get_all_base_mixes() -> dict:
    """
    Get all base mix mappings.

    Returns:
        Complete mapping dictionary
    """
    return BASE_MIX_TYPE_MAPPING.copy()
