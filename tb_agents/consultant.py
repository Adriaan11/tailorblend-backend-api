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

from agents import Agent
from config.settings import load_instructions
from tb_agents.database_loader import get_combined_database


def create_tailorblend_consultant(custom_instructions: str = None, model: str = "gpt-4.1-mini-2025-04-14") -> Agent:
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
        instructions = load_instructions()

    # Load complete database into agent memory
    # This gives the agent instant access to all ingredients and base mixes
    # without needing to query an external vector store
    database_context = get_combined_database()

    # Append database to instructions so agent has full context
    full_instructions = f"{instructions}\n\n{database_context}"

    # Create agent with complete database in memory
    agent = Agent(
        name="TailorBlend Consultant",
        instructions=full_instructions,

        # Use specified model (defaults to GPT-4.1 mini)
        # Model can be changed via API parameter for different performance/cost tradeoffs
        model=model,

        # No tools needed - all data is in the agent's context
        # This simplifies the architecture and eliminates vector store dependency
        tools=[],

        # No output_type specified = free-form conversation
        # Agent will naturally conclude when formulation is complete
        # We could add structured output later for API integration
    )

    return agent
