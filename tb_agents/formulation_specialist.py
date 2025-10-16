"""
Formulation Specialist Agent

This agent is a product configuration expert that selects the optimal base mix
and add-mix options based on ingredient requirements and patient preferences.

The agent has complete access to all base mixes and their customization options
loaded directly into its context.
"""

import json
from pathlib import Path
from agents import Agent
from backend.models import FormulationConfig, SupplementRecommendation


def load_base_mixes_data() -> str:
    """
    Load BaseAddMixes2.json and format for agent context.

    Returns formatted string containing all base mix and add-mix options
    that the agent can reference when configuring the formulation.
    """
    project_root = Path(__file__).parent.parent
    base_mixes_file = project_root / "spec" / "BaseAddMixes2.json"

    with open(base_mixes_file, 'r') as f:
        base_mixes = json.load(f)

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
    formatted_lines = ["AVAILABLE BASE MIXES & CUSTOMIZATION OPTIONS:", "=" * 80, ""]

    for base_id, base_info in sorted(base_mix_groups.items()):
        formatted_lines.append(f"\n{'*' * 80}")
        formatted_lines.append(f"BASE MIX #{base_id}: {base_info['name']}")
        formatted_lines.append(f"{'*' * 80}")

        for add_type, options in sorted(base_info['options'].items()):
            formatted_lines.append(f"\n  {add_type} Options:")
            for opt in options:
                default_marker = " [DEFAULT]" if opt['default'] else ""
                formatted_lines.append(f"    - ID {opt['id']}: {opt['name']}{default_marker}")

        formatted_lines.append("")  # Blank line between base mixes

    return "\n".join(formatted_lines)


def create_formulation_specialist() -> Agent:
    """
    Create the Formulation Specialist agent.

    This agent:
    - Receives supplement recommendations from Supplement Specialist
    - Selects optimal base mix (Shake Whey, Shake Vegan, Drink, Capsules)
    - Chooses appropriate add-mix options (flavor, protein, sweetener, etc.)
    - Respects ingredient delivery constraints
    - Considers patient preferences and dietary restrictions

    Returns:
        Agent configured with full base mix database and product expertise
    """

    # Load all base mixes into agent context
    base_mixes_data = load_base_mixes_data()

    instructions = f"""You are a formulation specialist expert in TailorBlend product configuration.

{base_mixes_data}

YOUR ROLE:
You receive a supplement recommendation (ingredients + dosages + constraints) and configure
the optimal base mix and add-mix options for delivery.

BASE MIX TYPES AVAILABLE:
1. Shake (Whey) - Base Mix #1: Whey protein shake, most popular
2. Shake (Vegan) - Base Mix #2: Plant-based protein shake for vegetarians/vegans
3. Drink - Base Mix #3: Light drink format, good for liquid-only ingredients
4. Capsules - Base Mix #4: Pill format, convenient but limited ingredient compatibility

DECISION CRITERIA:

1. DELIVERY CONSTRAINTS (HIGHEST PRIORITY):
   - If ANY ingredient says "ONLY AVAILABLE IN DRINKS", you MUST use Shake or Drink base
   - Capsules cannot accommodate liquid-only ingredients
   - Large dosages (>5g total) better suited for shakes/drinks

2. DIETARY PREFERENCES:
   - Vegan/Vegetarian → Base Mix #2 (Shake Vegan)
   - Dairy-sensitive → Base Mix #2 or #3
   - No preference → Base Mix #1 (Shake Whey - most popular)

3. ADD-MIX SELECTION:
   - Protein: Match base type (Whey → Whey Concentrate, Vegan → Pea Protein)
   - Flavor: Consider patient preferences, default to Decadent Dark Chocolate for shakes
   - Sweetener: Sucralose (default), or Stevia if preference stated
   - Thickness: Regular (default) unless specified

4. USER EXPERIENCE:
   - Shakes: Better for higher ingredient loads, more filling
   - Drinks: Lighter, faster to consume, good for on-the-go
   - Capsules: Most convenient but capacity limited

OUTPUT REQUIREMENTS:
You MUST return a structured FormulationConfig with:
- base_mix: Selected base with ID, name, and rationale
- add_mixes: All customization choices (protein, flavor, sweetener, etc.)
- ingredients: Pass through the ingredients from Supplement Specialist
- delivery_format: "shake", "drink", or "capsule"
- user_instructions: Clear directions on preparation and consumption
- formulation_rationale: Explanation of configuration decisions

EXAMPLE REASONING:
"Selected Shake (Vegan) base because patient is vegetarian and has Creatine (5g) which
requires liquid delivery. Chose Pea Protein for vegan compatibility, Vanilla Ice Cream
flavor for palatability, and Stevia sweetener for natural preference. Mix once daily
with 300ml water, consume post-workout for optimal absorption."
"""

    agent = Agent(
        name="Formulation Specialist",
        instructions=instructions,
        model="gpt-5-mini-2025-08-07",  # Using GPT-5 mini as requested
        output_type=FormulationConfig,  # Structured output
    )

    return agent
