"""
Supplement Specialist Agent

This agent is a clinical nutrition expert that selects optimal ingredients
and calculates appropriate dosages based on patient health goals and profile.

The agent has complete access to all 112 ingredients with their dosage ranges,
costs, and constraints loaded directly into its context.
"""

import json
from pathlib import Path
from agents import Agent
from backend.models import SupplementRecommendation


def load_ingredients_data() -> str:
    """
    Load Ingredients3.json and format for agent context.

    Returns formatted string containing all ingredient data that the agent
    can reference when making selections.
    """
    # Get path to spec folder (go up from tb_agents to project root, then into spec)
    project_root = Path(__file__).parent.parent
    ingredients_file = project_root / "spec" / "Ingredients3.json"

    with open(ingredients_file, 'r') as f:
        ingredients = json.load(f)

    # Format ingredients as readable text for agent
    formatted_lines = ["AVAILABLE INGREDIENTS DATABASE:", "=" * 80, ""]

    for ing in ingredients:
        # Get fields with safe fallbacks
        name = ing.get('name', 'Unknown')
        min_range = ing.get('minimumRange', ing.get('minimumrange', 'N/A'))
        rec_range = ing.get('reccomendedRange', ing.get('reccomendedrange', 'N/A'))
        max_range = ing.get('customerMaxRange', ing.get('customermaxrange', 'N/A'))
        unit = ing.get('unitOfMeasureName', ing.get('unitofmeasurename', 'units'))
        cost = ing.get('pricePer30Servings', ing.get('priceper30servings', '0.00'))
        overview = ing.get('overview', '')

        formatted_lines.append(f"• {name}")
        formatted_lines.append(f"  Dosage Range: {min_range} - {rec_range} {unit}")
        formatted_lines.append(f"  Max (Customer): {max_range} {unit}")
        formatted_lines.append(f"  Cost (30 servings): R{cost}")
        if overview:
            formatted_lines.append(f"  Notes: {overview}")
        formatted_lines.append("")  # Blank line between ingredients

    return "\n".join(formatted_lines)


def create_supplement_specialist() -> Agent:
    """
    Create the Supplement Specialist agent.

    This agent:
    - Analyzes patient health goals, conditions, and demographics
    - Selects appropriate ingredients from the database
    - Calculates personalized dosages within safe ranges
    - Considers interactions and contraindications
    - Provides clinical rationale for selections

    Returns:
        Agent configured with full ingredient database and clinical expertise
    """

    # Load all ingredients into agent context
    ingredients_data = load_ingredients_data()

    instructions = f"""You are a clinical supplement specialist with expertise in personalized nutrition.

{ingredients_data}

YOUR ROLE:
You analyze patient profiles and health goals to select optimal ingredients with appropriate dosages.

IMPORTANT CONSTRAINTS:
1. Some ingredients are ONLY AVAILABLE IN DRINKS (noted in overview)
2. Dosages must be within the minimum-maximum range for each ingredient
3. Consider cost - aim for balance between efficacy and affordability
4. Flag any potential medication interactions (if medications provided)
5. Note any ingredients that contain caffeine or are unsuitable for certain conditions

PATIENT PROFILE ANALYSIS:
- Consider age, weight, sex for dosage calculations
- Map health goals to nutrient needs
- Identify deficiencies based on symptoms/goals
- Consider dietary preferences (vegan → avoid dairy-based ingredients)
- Account for medical conditions and medications

OUTPUT REQUIREMENTS:
You MUST return a structured SupplementRecommendation with:
- ingredients: List of selected ingredients with specific dosages and rationale
- delivery_constraints: Any requirements like "L-ARGININE must be in drink"
- total_estimated_cost: Sum of all ingredient costs
- clinical_rationale: Overall explanation of the formulation approach
- safety_notes: Any warnings or interactions to be aware of

Be precise with dosages - use the recommended range as a starting point and adjust based on:
- Patient weight (lighter = lower end, heavier = higher end)
- Age (elderly = conservative, young adults = moderate)
- Health goal intensity (mild symptoms = lower, severe = higher)
- Synergistic effects (combining ingredients may allow lower individual dosages)

EXAMPLE REASONING:
"For sleep + stress: Selected Magnesium Glycinate (400mg - upper range due to significant sleep issues),
L-Theanine (200mg - moderate dose for stress), and Ashwagandha (300mg - standard adaptogenic dose).
Total cost: R163.50. Note: Evening timing recommended for sleep support."
"""

    agent = Agent(
        name="Supplement Specialist",
        instructions=instructions,
        model="gpt-5-mini-2025-08-07",  # Using GPT-5 mini as requested
        output_type=SupplementRecommendation,  # Structured output
    )

    return agent
