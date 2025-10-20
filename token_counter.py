"""
Token Counter for TailorBlend AI Consultant

Utilities for counting tokens and calculating costs in South African Rands.
"""

import tiktoken
from typing import Dict


# Constants
USD_TO_ZAR = 17.50  # Exchange rate (October 2025)

# Model-specific pricing (USD per 1M tokens)
# Based on OpenAI API pricing as of August-October 2025
MODEL_PRICING = {
    "gpt-4.1-mini-2025-04-14": {"input": 0.40, "output": 1.60},
    "gpt-5": {"input": 2.50, "output": 10.00},  # GPT-5 full reasoning model
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    "gpt-5-chat-latest": {"input": 1.25, "output": 10.00},
}

# Legacy constants (kept for backward compatibility)
GPT5_MINI_INPUT_COST_PER_1M = 0.25  # USD per 1M tokens
GPT5_MINI_OUTPUT_COST_PER_1M = 2.00  # USD per 1M tokens

# Initialize tokenizer for gpt-5-mini
_encoder = None


def get_encoder():
    """
    Get or create the tiktoken encoder for gpt-5-mini.

    Cached globally to avoid reloading on every call.

    Returns:
        tiktoken.Encoding: Encoder for gpt-5-mini
    """
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.encoding_for_model("gpt-5-mini")
    return _encoder


def count_tokens(text: str) -> int:
    """
    Count tokens in a text string using OpenAI's tiktoken.

    Args:
        text: Text to count tokens for

    Returns:
        int: Number of tokens

    Example:
        >>> count_tokens("Hello, world!")
        4
    """
    if not text:
        return 0

    encoder = get_encoder()
    tokens = encoder.encode(text)
    return len(tokens)


def calculate_cost_zar(input_tokens: int, output_tokens: int = 0, model: str = "gpt-4.1-mini-2025-04-14") -> Dict[str, float]:
    """
    Calculate cost in South African Rands for given token counts.

    Supports multiple models with different pricing:
    - GPT-4.1-mini: $0.40 input / $1.60 output per 1M tokens
    - GPT-5: $2.50 input / $10.00 output per 1M tokens (most capable)
    - GPT-5-mini: $0.25 input / $2.00 output per 1M tokens
    - GPT-5-nano: $0.05 input / $0.40 output per 1M tokens
    - GPT-5-chat: $1.25 input / $10.00 output per 1M tokens
    - Exchange rate: R17.50 per USD

    Args:
        input_tokens: Number of input (prompt) tokens
        output_tokens: Number of output (completion) tokens
        model: Model identifier (defaults to gpt-4.1-mini-2025-04-14)

    Returns:
        Dict with cost breakdown:
        - input_cost_zar: Cost of input tokens in ZAR
        - output_cost_zar: Cost of output tokens in ZAR
        - total_cost_zar: Total cost in ZAR
        - total_tokens: Total token count

    Example:
        >>> calculate_cost_zar(1000, 500, "gpt-5-nano-2025-08-07")
        {
            'input_cost_zar': 0.00088,
            'output_cost_zar': 0.0035,
            'total_cost_zar': 0.00438,
            'total_tokens': 1500
        }
    """
    # Get pricing for the specified model, fallback to gpt-4.1-mini
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4.1-mini-2025-04-14"])

    # Calculate USD costs
    input_cost_usd = (input_tokens / 1_000_000) * pricing["input"]
    output_cost_usd = (output_tokens / 1_000_000) * pricing["output"]

    # Convert to ZAR
    input_cost_zar = input_cost_usd * USD_TO_ZAR
    output_cost_zar = output_cost_usd * USD_TO_ZAR
    total_cost_zar = input_cost_zar + output_cost_zar

    return {
        "input_cost_zar": input_cost_zar,
        "output_cost_zar": output_cost_zar,
        "total_cost_zar": total_cost_zar,
        "total_tokens": input_tokens + output_tokens,
    }


def format_cost_zar(cost: float) -> str:
    """
    Format cost in ZAR for display.

    Uses appropriate precision based on amount:
    - < R0.01: 4 decimal places
    - >= R0.01: 2 decimal places

    Args:
        cost: Cost in ZAR

    Returns:
        str: Formatted cost string

    Example:
        >>> format_cost_zar(0.0044)
        'R0.0044'
        >>> format_cost_zar(0.15)
        'R0.15'
        >>> format_cost_zar(1.5)
        'R1.50'
    """
    if cost < 0.01:
        return f"R{cost:.4f}"
    else:
        return f"R{cost:.2f}"


def format_tokens(count: int) -> str:
    """
    Format token count for display with thousands separators.

    Args:
        count: Token count

    Returns:
        str: Formatted token count

    Example:
        >>> format_tokens(1847)
        '1,847'
        >>> format_tokens(1234567)
        '1,234,567'
    """
    return f"{count:,}"
