"""
TailorBlend Consultant Agent

The main conversational agent that guides users through creating
personalized supplement blends.

This agent:
1. Conducts 4-phase consultation (Registration → Discovery → Assessment → Formulation)
2. Uses OpenAI vector store (FileSearchTool) to lookup ingredients and base mix options
3. Maintains conversation in memory (no persistence)
4. Provides expert recommendations with reasoning
"""

import logging
from agents import Agent, FileSearchTool, ModelSettings
from config.settings import load_instructions
from tb_agents.tools import create_personalized_blend

# Configure module logger
logger = logging.getLogger(__name__)


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
    vector_store_id: str,
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

    The agent has access to vector store via FileSearchTool:
    - Uses OpenAI semantic search to look up ingredients
    - Searches for base mix options and customization
    - Dynamic retrieval (only relevant data loaded per query)

    Args:
        vector_store_id: OpenAI vector store ID (vs_xyz) to use for ingredient lookups.
                        Required parameter - specifies which dataset to query.
        custom_instructions: Optional custom instructions to use instead of file.
                            If None, loads from spec/instructions.txt
        model: OpenAI model to use. Defaults to "gpt-5".
               Supported models:
               - gpt-4.1-mini-2025-04-14 (default, fast and cost-effective)
               - gpt-5-2025-08-07 (most capable)
               - gpt-5-mini-2025-08-07
               - gpt-5-nano-2025-08-07
               - gpt-5-chat-latest

    Returns:
        Agent: Configured TailorBlend consultant agent with FileSearchTool

    Example:
        >>> from tb_agents.consultant import create_tailorblend_consultant
        >>> from agents import Runner
        >>>
        >>> # Create agent with vector store
        >>> agent = await create_tailorblend_consultant(
        ...     vector_store_id="vs_xyz123"
        ... )
        >>>
        >>> # Use custom instructions
        >>> custom = "Be more concise..."
        >>> agent = await create_tailorblend_consultant(
        ...     vector_store_id="vs_xyz123",
        ...     custom_instructions=custom
        ... )
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

    # Add tool usage guidance if not already present
    needs_tool_instruction = "file_search" not in instructions.lower()

    if needs_tool_instruction:
        tool_guidance = """
## Using the Ingredient & Base Mix Database

You have access to a file_search tool that contains:
- Complete ingredient database with dosages, costs, and constraints
- Base mix types and customization options

Use this tool to:
- Look up specific ingredients when users ask about them
- Find ingredients matching health goals or dietary needs
- Research ingredient interactions and dosages
- Verify base mix compatibility with recommendations

Search naturally: e.g., "magnesium for sleep", "vegan protein sources", etc.
The tool will return relevant items with full details for you to reference.
"""
        instructions = f"{instructions}\n{tool_guidance}"
        logger.debug("Added tool usage guidance to instructions")

    # Add markdown formatting instruction
    needs_markdown_instruction = "markdown" not in instructions.lower()

    if needs_markdown_instruction:
        # Append markdown formatting requirement
        full_instructions = f"{instructions}\n\n{MARKDOWN_FORMATTING_INSTRUCTION}"
        logger.debug("Appended markdown formatting instruction to agent")
    else:
        # Instructions already mention markdown, don't duplicate
        full_instructions = instructions
        logger.debug("Instructions already contain markdown guidance, skipping append")

    # Log first 500 characters of final instructions for verification
    instructions_preview = full_instructions[:500].replace('\n', ' ')
    logger.debug("Final instructions preview: %s...", instructions_preview)

    # Create agent with FileSearchTool for vector store queries
    agent = Agent(
        name="TailorBlend Consultant",
        instructions=full_instructions,

        # Use specified model (defaults to GPT-5)
        # Model can be changed via API parameter for different performance/cost tradeoffs
        model=model,

        # Model settings (for GPT-5: reasoning effort, verbosity, etc.)
        model_settings=model_settings if model_settings else ModelSettings(),

        # Tools available to the agent
        tools=[
            # NEW: Search vector store for ingredient/base mix information
            # FileSearchTool automatically calls OpenAI's semantic search
            # Returns relevant items from the active vector store
            FileSearchTool(
                vector_store_ids=[vector_store_id],
                max_num_results=10,
                include_search_results=True
            ),
            # EXISTING: Create actual supplement blends in production system
            # Calls TailorBlend API after consultation is complete
            create_personalized_blend
        ],

        # No output_type specified = free-form conversation
        # Agent will naturally conclude when formulation is complete
        # We could add structured output later for API integration
    )

    logger.info(f"✅ Created consultant agent with vector store: {vector_store_id}")
    return agent
