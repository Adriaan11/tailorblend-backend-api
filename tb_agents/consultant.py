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

from agents import Agent, FileSearchTool
from config.settings import load_instructions, VECTOR_STORE_ID


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

    The agent uses file_search to query a vector store containing:
    - 111 ingredients with dosages, constraints, and health categories
    - 4 base mix types with 68 customization options

    Args:
        custom_instructions: Optional custom instructions to use instead of file.
                            If None, loads from spec/instructions.txt
        model: OpenAI model to use. Defaults to "gpt-4.1-mini-2025-04-14".
               Supported models:
               - gpt-5-mini-2025-08-07
               - gpt-5-nano-2025-08-07
               - gpt-5-chat-latest
               - gpt-4.1-mini-2025-04-14 (default)

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

    # Create file search tool connected to vector store
    # The vector store contains ingredients and base mix databases
    file_search = FileSearchTool(
        vector_store_ids=[VECTOR_STORE_ID],
        max_num_results=30  # Return top 30 most relevant results for comprehensive formulation
    )

    # Create agent with file_search access to vector store
    agent = Agent(
        name="TailorBlend Consultant",
        instructions=instructions,

        # Use specified model (defaults to GPT-4.1 mini)
        # Model can be changed via API parameter for different performance/cost tradeoffs
        model=model,

        # Enable file search for vector store queries
        # Agent can query: "Find ingredients for energy and focus"
        # or: "What are the default add-mixes for Drink base?"
        tools=[file_search],

        # No output_type specified = free-form conversation
        # Agent will naturally conclude when formulation is complete
        # We could add structured output later for API integration
    )

    return agent
