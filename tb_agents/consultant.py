"""
TailorBlend Consultant Agent

The main conversational agent that guides users through creating
personalized supplement blends.

This agent:
1. Conducts 4-phase consultation (Registration → Discovery → Assessment → Formulation)
2. Uses vector store to lookup ingredients and base mix options
3. Maintains conversation in memory (no persistence)
4. Provides expert recommendations with reasoning
"""

import sys
from agents import Agent, ModelSettings
from config.settings import load_instructions
from tb_agents.database_loader import get_combined_database
from tb_agents.tools import create_personalized_blend


# Markdown formatting instruction for all agent responses
# Includes "Formatting re-enabled" for GPT-5/reasoning models (o1, o3, o3-mini)
# and explicit formatting requirements for GPT-4.1 and clarity
MARKDOWN_FORMATTING_INSTRUCTION = """Formatting re-enabled

═══════════════════════════════════════════════════════════════
CRITICAL: OUTPUT FORMAT REQUIREMENT
═══════════════════════════════════════════════════════════════

You must synthesize all consultation information into well-structured
markdown responses. This is not optional.

Required formatting:
- **Bold** for supplement names, dosages, base mix types, and key terms
- Bullet lists (- or •) for ingredient lists, benefits, and recommendations
- Numbered lists (1., 2., 3.) for sequential consultation steps
- Headers (## for main sections, ### for subsections) to organize content
- `code-style formatting` for precise measurements (e.g., `500mg`, `2x daily`)

Every response must use markdown syntax for clarity and professional
presentation. Plain text responses are not acceptable.

═══════════════════════════════════════════════════════════════
"""


async def create_tailorblend_consultant(
    custom_instructions: str = None,
    model: str = "gpt-5",
    model_settings: ModelSettings = None
) -> Agent:
    """
    Create the main TailorBlend consultant agent.

    The agent's behavior is defined by instructions.txt which contains:
    - Core identity and role (friendly South African consultant)
    - Conversation style guidelines (crisp, concise, adaptive)
    - Value proposition framing (complete solution, not just another supplement)
    - 4-phase workflow (Registration → Discovery → Assessment → Formulation)
    - Technical requirements (base mix types, add-mix selection, ingredient constraints)
    - API integration specs (when implemented)

    The agent has direct access to the complete database loaded into memory:
    - 111 ingredients with dosages, constraints, and health categories
    - 4 base mix types with 68 customization options

    Args:
        custom_instructions: Optional custom instructions to use instead of file.
                            If None, loads from spec/instructions.txt
        model: OpenAI model to use. Defaults to "gpt-4.1-mini-2025-04-14".
               Supported models:
               - gpt-4.1-mini-2025-04-14 (default, fast and cost-effective)
               - gpt-5-2025-08-07 (most capable)
               - gpt-5-mini-2025-08-07
               - gpt-5-nano-2025-08-07
               - gpt-5-chat-latest

    Returns:
        Agent: Configured TailorBlend consultant agent

    Example:
        >>> from tb_agents.consultant import create_tailorblend_consultant
        >>> from agents import Runner
        >>>
        >>> # Use default instructions and model
        >>> agent = create_tailorblend_consultant()
        >>>
        >>> # Use custom instructions
        >>> custom = "Be more concise..."
        >>> agent = create_tailorblend_consultant(custom_instructions=custom)
        >>>
        >>> # Use different model
        >>> agent = create_tailorblend_consultant(model="gpt-5-mini-2025-08-07")
        >>>
        >>> result = await Runner.run(
        ...     agent,
        ...     "Hi, I'd like to create a personalized supplement"
        ... )
    """

    # Load instructions from custom parameter or file
    if custom_instructions:
        instructions = custom_instructions
    else:
        # Load full instructions from spec/instructions.txt
        # This is the "system prompt" containing all business logic
        instructions = await load_instructions()

    # Load complete database into agent memory
    # This gives the agent instant access to all ingredients and base mixes
    # without needing to query an external vector store
    database_context = await get_combined_database()

    # Smart detection: Only append markdown formatting if not already mentioned
    # This prevents duplication if custom_instructions already specify markdown
    needs_markdown_instruction = "markdown" not in instructions.lower()

    if needs_markdown_instruction:
        # Append markdown formatting requirement
        full_instructions = f"{instructions}\n\n{database_context}{MARKDOWN_FORMATTING_INSTRUCTION}"
        print(f"✨ [CONSULTANT] Appended markdown formatting instruction to agent", file=sys.stderr)
    else:
        # Instructions already mention markdown, don't duplicate
        full_instructions = f"{instructions}\n\n{database_context}"
        print(f"✨ [CONSULTANT] Instructions already contain markdown guidance, skipping append", file=sys.stderr)

    # Log first 500 characters of final instructions for verification
    instructions_preview = full_instructions[:500].replace('\n', ' ')
    print(f"📋 [CONSULTANT] Final instructions preview: {instructions_preview}...", file=sys.stderr)

    # Create agent with complete database in memory
    agent = Agent(
        name="TailorBlend Consultant",
        instructions=full_instructions,

        # Use specified model (defaults to GPT-4.1 mini)
        # Model can be changed via API parameter for different performance/cost tradeoffs
        model=model,

        # Model settings (for GPT-5: reasoning effort, verbosity, etc.)
        model_settings=model_settings if model_settings else ModelSettings(),

        # Function tools available to the agent
        # - create_personalized_blend: Calls production API to create actual supplement blends
        #   After consultation, the agent uses this to generate real products with pricing,
        #   nutritional labels, and shareable URLs
        tools=[create_personalized_blend],

        # No output_type specified = free-form conversation
        # Agent will naturally conclude when formulation is complete
        # We could add structured output later for API integration
    )

    return agent
