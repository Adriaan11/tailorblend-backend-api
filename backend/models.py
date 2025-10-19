"""
Pydantic Models for TailorBlend AI Consultant API

Data models for request/response validation and serialization.
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class ModelSettingsRequest(BaseModel):
    """Model configuration settings for controlling LLM behavior"""
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Controls randomness (0=deterministic, 2=very creative)")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling threshold")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Penalty for token frequency (reduces repetition)")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Penalty for token presence (encourages new topics)")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum number of output tokens")
    verbosity: Optional[str] = Field(None, pattern="^(low|medium|high)$", description="Response verbosity level")
    tool_choice: Optional[str] = Field(None, description="Tool selection strategy (auto, required, none, or specific tool name)")
    parallel_tool_calls: Optional[bool] = Field(None, description="Allow multiple parallel tool calls")
    truncation: Optional[str] = Field(None, pattern="^(auto|disabled)$", description="Context truncation strategy")
    store: Optional[bool] = Field(None, description="Whether to store response for later retrieval")
    include_usage: Optional[bool] = Field(None, description="Include usage information in response")
    top_logprobs: Optional[int] = Field(None, ge=0, le=20, description="Number of top token log probabilities to return")
    metadata: Optional[Dict[str, str]] = Field(None, description="Custom metadata key-value pairs")


class ChatRequest(BaseModel):
    """Request model for chat endpoint (if using POST in future)"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session identifier")
    custom_instructions: Optional[str] = Field(None, description="Custom instructions override")
    model_settings: Optional[ModelSettingsRequest] = Field(None, description="Optional model configuration settings")


class SessionStatsResponse(BaseModel):
    """Response model for session statistics"""
    session_id: str
    message_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    cost_zar: float
    cost_formatted: str


class InstructionsResponse(BaseModel):
    """Response model for instructions endpoint"""
    success: bool
    sections: Optional[Dict[str, str]] = None
    full_text: Optional[str] = None
    error: Optional[str] = None


class InstructionsUpdateRequest(BaseModel):
    """Request model for updating instructions"""
    sections: Dict[str, str] = Field(..., description="Updated instruction sections")


class InstructionsUpdateResponse(BaseModel):
    """Response model for instruction updates"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class SessionResetRequest(BaseModel):
    """Request model for session reset"""
    session_id: str = Field(..., description="Session identifier to reset")


class SessionResetResponse(BaseModel):
    """Response model for session reset"""
    success: bool
    message: str


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    service: str
    version: str


# ============================================================================
# Multi-Agent Blend Models
# ============================================================================

class SelectedIngredient(BaseModel):
    """An ingredient selected by the Supplement Specialist"""
    name: str = Field(..., description="Ingredient name")
    dosage: float = Field(..., description="Dosage amount")
    unit: str = Field(..., description="Unit of measurement (mg, g, mcg)")
    rationale: str = Field(..., description="Why this ingredient was selected")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost per 30 servings")


class SupplementRecommendation(BaseModel):
    """Structured output from Supplement Specialist agent"""
    ingredients: List[SelectedIngredient] = Field(..., description="Selected ingredients with dosages")
    delivery_constraints: List[str] = Field(default_factory=list, description="Constraints like 'must be in liquid'")
    total_estimated_cost: float = Field(..., description="Total estimated cost")
    clinical_rationale: str = Field(..., description="Overall clinical reasoning")
    safety_notes: Optional[str] = Field(None, description="Safety considerations or warnings")


class BaseMixConfig(BaseModel):
    """Selected base mix configuration"""
    base_mix_id: int
    base_mix_name: str
    rationale: str = Field(..., description="Why this base was chosen")


class AddMixConfig(BaseModel):
    """Selected add-mix option"""
    add_mix_type: str  # "Protein", "Flavour", "Sweetener", etc.
    add_mix_id: int
    add_mix_name: str


class FormulationConfig(BaseModel):
    """Structured output from Formulation Specialist agent"""
    base_mix: BaseMixConfig
    add_mixes: List[AddMixConfig] = Field(..., description="Selected add-mix options")
    ingredients: List[SelectedIngredient] = Field(..., description="Ingredients from Supplement Specialist")
    delivery_format: str = Field(..., description="shake, drink, or capsule")
    user_instructions: str = Field(..., description="How to prepare and consume")
    formulation_rationale: str = Field(..., description="Why this configuration was chosen")


class MultiAgentBlendRequest(BaseModel):
    """Request model for multi-agent blend creation"""
    session_id: str = Field(..., description="Session identifier")
    patient_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    weight: Optional[float] = None
    health_goals: str = Field(..., description="Health goals and concerns")
    dietary_preferences: Optional[str] = Field(None, description="vegan, vegetarian, keto, etc.")
    medical_conditions: Optional[str] = Field(None, description="Chronic conditions")
    medications: Optional[str] = Field(None, description="Current medications")
    additional_info: Optional[str] = Field(None, description="Any other relevant information")


class AgentStep(BaseModel):
    """Represents a step in the multi-agent workflow for streaming"""
    agent_name: str = Field(..., description="Name of the agent")
    step_type: str = Field(..., description="thinking, result, error")
    content: str = Field(..., description="Step content or message")
    data: Optional[Dict] = Field(None, description="Optional structured data")
