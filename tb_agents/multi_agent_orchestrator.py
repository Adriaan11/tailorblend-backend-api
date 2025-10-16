"""
Multi-Agent Orchestrator

Coordinates the workflow between Supplement Specialist and Formulation Specialist agents.

Flow:
1. User provides health profile + goals
2. Supplement Specialist analyzes and selects ingredients
3. Formulation Specialist configures base mix and delivery
4. Return combined formulation to user
"""

from typing import AsyncGenerator, Dict
from agents import Runner
from backend.models import (
    MultiAgentBlendRequest,
    AgentStep,
    SupplementRecommendation,
    FormulationConfig
)
from tb_agents.supplement_specialist import create_supplement_specialist
from tb_agents.formulation_specialist import create_formulation_specialist


class MultiAgentOrchestrator:
    """
    Orchestrates the multi-agent formulation workflow.

    This class manages the interaction between specialized agents,
    provides progress updates via streaming, and handles errors gracefully.
    """

    def __init__(self):
        """Initialize both specialized agents."""
        self.supplement_agent = create_supplement_specialist()
        self.formulation_agent = create_formulation_specialist()

    async def create_blend(
        self,
        request: MultiAgentBlendRequest
    ) -> AsyncGenerator[AgentStep, None]:
        """
        Execute the multi-agent workflow and stream progress.

        Args:
            request: User's health profile and goals

        Yields:
            AgentStep: Progress updates from each agent

        Returns:
            Final formulation combining both agents' outputs
        """

        try:
            # ====================================================================
            # STEP 1: Supplement Specialist - Select Ingredients
            # ====================================================================

            yield AgentStep(
                agent_name="Supplement Specialist",
                step_type="thinking",
                content="Analyzing health profile and selecting optimal ingredients..."
            )

            # Build input for Supplement Specialist
            patient_profile = self._build_patient_profile(request)

            # Run Supplement Specialist
            supplement_result = await Runner.run(
                self.supplement_agent,
                input=patient_profile
            )

            # Extract structured output
            supplement_recommendation: SupplementRecommendation = supplement_result.final_output

            # Stream result
            yield AgentStep(
                agent_name="Supplement Specialist",
                step_type="result",
                content=f"Selected {len(supplement_recommendation.ingredients)} ingredients. "
                       f"Estimated cost: R{supplement_recommendation.total_estimated_cost:.2f}",
                data={
                    "ingredients": [ing.model_dump() for ing in supplement_recommendation.ingredients],
                    "clinical_rationale": supplement_recommendation.clinical_rationale,
                    "delivery_constraints": supplement_recommendation.delivery_constraints
                }
            )

            # ====================================================================
            # STEP 2: Formulation Specialist - Configure Delivery
            # ====================================================================

            yield AgentStep(
                agent_name="Formulation Specialist",
                step_type="thinking",
                content="Configuring optimal base mix and delivery format..."
            )

            # Build input for Formulation Specialist
            formulation_input = self._build_formulation_input(
                request,
                supplement_recommendation
            )

            # Run Formulation Specialist
            formulation_result = await Runner.run(
                self.formulation_agent,
                input=formulation_input
            )

            # Extract structured output
            formulation_config: FormulationConfig = formulation_result.final_output

            # Stream result
            yield AgentStep(
                agent_name="Formulation Specialist",
                step_type="result",
                content=f"Configured {formulation_config.base_mix.base_mix_name} with "
                       f"{len(formulation_config.add_mixes)} customizations.",
                data={
                    "base_mix": formulation_config.base_mix.model_dump(),
                    "add_mixes": [am.model_dump() for am in formulation_config.add_mixes],
                    "delivery_format": formulation_config.delivery_format,
                    "user_instructions": formulation_config.user_instructions,
                    "formulation_rationale": formulation_config.formulation_rationale
                }
            )

            # ====================================================================
            # FINAL STEP: Complete Formulation
            # ====================================================================

            yield AgentStep(
                agent_name="Multi-Agent System",
                step_type="result",
                content="✅ Formulation complete!",
                data={
                    "supplement_recommendation": supplement_recommendation.model_dump(),
                    "formulation_config": formulation_config.model_dump(),
                    "summary": {
                        "total_ingredients": len(supplement_recommendation.ingredients),
                        "total_cost": supplement_recommendation.total_estimated_cost,
                        "base_mix": formulation_config.base_mix.base_mix_name,
                        "delivery_format": formulation_config.delivery_format
                    }
                }
            )

        except Exception as e:
            # Stream error information
            yield AgentStep(
                agent_name="Multi-Agent System",
                step_type="error",
                content=f"Error during formulation: {str(e)}",
                data={"error_type": type(e).__name__, "error_message": str(e)}
            )

    def _build_patient_profile(self, request: MultiAgentBlendRequest) -> str:
        """
        Convert request into natural language input for Supplement Specialist.

        Args:
            request: User's input data

        Returns:
            Formatted string describing patient profile and goals
        """
        profile_parts = []

        # Basic demographics
        if request.patient_name:
            profile_parts.append(f"Patient: {request.patient_name}")

        demographics = []
        if request.age:
            demographics.append(f"{request.age} years old")
        if request.sex:
            demographics.append(request.sex.lower())
        if request.weight:
            demographics.append(f"{request.weight}kg")

        if demographics:
            profile_parts.append("Demographics: " + ", ".join(demographics))

        # Health goals (required)
        profile_parts.append(f"Health Goals: {request.health_goals}")

        # Optional information
        if request.dietary_preferences:
            profile_parts.append(f"Dietary: {request.dietary_preferences}")

        if request.medical_conditions:
            profile_parts.append(f"Medical Conditions: {request.medical_conditions}")

        if request.medications:
            profile_parts.append(f"Current Medications: {request.medications}")

        if request.additional_info:
            profile_parts.append(f"Additional Info: {request.additional_info}")

        return "\n".join(profile_parts)

    def _build_formulation_input(
        self,
        request: MultiAgentBlendRequest,
        supplement_rec: SupplementRecommendation
    ) -> str:
        """
        Convert supplement recommendation + patient prefs into input for Formulation Specialist.

        Args:
            request: User's original request
            supplement_rec: Output from Supplement Specialist

        Returns:
            Formatted string for Formulation Specialist
        """
        input_parts = []

        # Ingredients selected
        input_parts.append("SELECTED INGREDIENTS:")
        for ing in supplement_rec.ingredients:
            input_parts.append(f"  - {ing.name}: {ing.dosage}{ing.unit}")

        # Delivery constraints
        if supplement_rec.delivery_constraints:
            input_parts.append("\nDELIVERY CONSTRAINTS:")
            for constraint in supplement_rec.delivery_constraints:
                input_parts.append(f"  - {constraint}")

        # Patient preferences
        input_parts.append("\nPATIENT PREFERENCES:")
        if request.dietary_preferences:
            input_parts.append(f"  - Dietary: {request.dietary_preferences}")
        if request.additional_info:
            input_parts.append(f"  - Additional: {request.additional_info}")

        return "\n".join(input_parts)
