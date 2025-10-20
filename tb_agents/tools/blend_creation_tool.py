"""
Blend Creation Tool

Function tool that enables the AI agent to create actual supplement blends
in the production system via the TailorBlend API.

This tool translates AI formulations into production API requests and returns
product details including URL, pricing, and nutritional information.
"""

import uuid
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import httpx
from agents import function_tool
from pydantic import BaseModel, Field

# Import base mix type ID mappings
from config.base_mix_mappings import get_base_mix_info


# ============================================================================
# CONFIGURATION
# ============================================================================

# Production API endpoint
PRODUCTION_API_URL = "https://api.tailorblend.co.za/api/v1/blend/aicreateblend"

# Test profile configuration (from request.json example)
TEST_PROFILE_ID = 641221
TEST_PROFILE_EMAIL = "ai.consultant@tailorblend.co.za"

# Template ID (from instructions.txt: ALWAYS "31")
TEMPLATE_ID = "31"

# Blend configuration defaults
DEFAULT_NUMBER_OF_SERVINGS = 30
DEFAULT_SENDER_ACCOUNT = "orders.tailorblend.co.za"
DEFAULT_REFERRER = "AI_CONSULTANT"


# ============================================================================
# PYDANTIC MODELS FOR STRICT SCHEMA VALIDATION
# ============================================================================

class IngredientInput(BaseModel):
    """Input model for ingredient specification"""
    ingredientId: int = Field(..., description="Database ingredient ID")
    name: str = Field(..., description="Ingredient name")
    amount: float = Field(..., description="Amount in mg or g")
    description: str = Field(default="", description="Brief benefit description")


class NutritionalInfo(BaseModel):
    """Nutritional information per serving"""
    calories: int = Field(default=0)
    protein: float = Field(default=0.0)
    carbohydrates: float = Field(default=0.0)
    fats: float = Field(default=0.0)
    fiber: float = Field(default=0.0)
    energy: float = Field(default=0.0)


class BlendCreationResponse(BaseModel):
    """Response from blend creation API"""
    success: bool
    errors: List[str] = Field(default_factory=list)
    blend_url: str = Field(default="")
    product_image_url: str = Field(default="")
    nutritional_label_url: str = Field(default="")
    blend_name: str
    price: float = Field(default=0.0)
    servings: int = Field(default=0)
    base_mix: str = Field(default="")
    nutritional_info: NutritionalInfo = Field(default_factory=NutritionalInfo)
    ingredients: List[dict] = Field(default_factory=list)  # Keep as dict - comes from API
    add_mixes: List[dict] = Field(default_factory=list)    # Keep as dict - comes from API


# ============================================================================
# FUNCTION TOOL DEFINITION
# ============================================================================

@function_tool
async def create_personalized_blend(
    # User Profile Information
    user_first_name: str,
    user_last_name: str,
    user_email: str,
    user_gender: str,
    user_age: int,

    # Blend Metadata
    blend_description: str,
    formulation_notes: str,
    blend_name: str,

    # Base Mix Selection (required before optional parameters)
    base_mix_id: int,  # Must be 1, 2, 6, or 8

    # Optional Parameters
    max_price: float = 3000.0,
    number_of_servings: int = DEFAULT_NUMBER_OF_SERVINGS,

    # Add-Mixes (flavors, sweeteners, thickness, etc.)
    add_mix_ids: Optional[List[int]] = None,

    # Active Ingredients (with IDs and amounts)
    ingredients: Optional[List[IngredientInput]] = None,

) -> BlendCreationResponse:
    """
    Create a personalized supplement blend in the TailorBlend production system.

    This tool should be called by the AI ONLY when it has:
    1. Completed a full user consultation
    2. Gathered all required profile information
    3. Selected appropriate ingredients with precise dosages
    4. Chosen a suitable base mix type
    5. Picked complementary add-mixes (flavors, sweeteners)

    Args:
        user_first_name: User's first name
        user_last_name: User's last name
        user_email: User's email address
        user_gender: User's gender ("Male", "Female", or "Other")
        user_age: User's age in years

        blend_description: Brief description of blend purpose (e.g., "Energy and focus support")
        formulation_notes: AI's reasoning for ingredient selection
        blend_name: Personalized blend name (e.g., "John's Energy Formula")
        max_price: Maximum price in ZAR (default: 3000.00)
        number_of_servings: Number of servings per container (default: 30)

        base_mix_id: Base mix type ID from database:
            - 1 = Shake (Whey) - for high protein, muscle support
            - 2 = Drink - for easy mixing, versatile use
            - 6 = Nutriblend - F - for specific formulations
            - 8 = Shake (Vegan) - for plant-based diets

        add_mix_ids: List of add-mix IDs (flavors, sweeteners, etc.) from database
            Example: [38, 58] = Passion Fruit flavor + Xylitol sweetener

        ingredients: List of IngredientInput models with required fields:
            Example: [
                IngredientInput(ingredientId=2, name="ALPHA LIPOIC ACID", amount=35.0, description="Antioxidant"),
                IngredientInput(ingredientId=5, name="BETA ALANINE", amount=1.0, description="Endurance")
            ]
            - ingredientId (int): ID from database
            - name (str): Ingredient name
            - amount (float): Amount in mg or g (use unit from database)
            - description (str): Brief description or benefit

    Returns:
        BlendCreationResponse containing:
        - success (bool): Whether blend was created successfully
        - blend_url (str): URL to view/purchase the blend
        - blend_name (str): Final blend name
        - price (float): Price in ZAR
        - servings (int): Number of servings
        - nutritional_info (NutritionalInfo): Calories, protein, carbs, fats, etc.
        - errors (List[str]): Any error messages (empty if successful)

    Raises:
        ValueError: If base_mix_id is invalid
        httpx.HTTPError: If API call fails

    Example:
        result = await create_personalized_blend(
            user_first_name="John",
            user_last_name="Smith",
            user_email="john@example.com",
            user_gender="Male",
            user_age=35,
            blend_description="Energy and mental clarity support for busy professional",
            formulation_notes="Selected B-complex for energy, L-theanine for calm focus",
            blend_name="John's Focus Formula",
            base_mix_id=2,  # Drink
            add_mix_ids=[38, 58],  # Passion fruit + Xylitol
            ingredients=[
                IngredientInput(ingredientId=2, name="ALPHA LIPOIC ACID", amount=35.0, description="Antioxidant"),
                IngredientInput(ingredientId=5, name="BETA ALANINE", amount=1.0, description="Endurance")
            ]
        )
    """

    print(f"🔧 [BLEND TOOL] Creating blend: {blend_name}", file=sys.stderr)
    print(f"🔧 [BLEND TOOL] User: {user_first_name} {user_last_name} ({user_age} {user_gender})", file=sys.stderr)
    print(f"🔧 [BLEND TOOL] Base Mix ID: {base_mix_id}", file=sys.stderr)
    print(f"🔧 [BLEND TOOL] Ingredients: {len(ingredients or [])} selected", file=sys.stderr)
    print(f"🔧 [BLEND TOOL] Add-Mixes: {len(add_mix_ids or [])} selected", file=sys.stderr)

    try:
        # Get base mix information including typeId
        base_mix_info = get_base_mix_info(base_mix_id)
        print(f"🔧 [BLEND TOOL] Base Mix: {base_mix_info['name']} (TypeID: {base_mix_info['typeId']})", file=sys.stderr)

        # Build complete API request
        api_request = _build_api_request(
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            user_email=user_email,
            user_gender=user_gender,
            user_age=user_age,
            blend_description=blend_description,
            formulation_notes=formulation_notes,
            blend_name=blend_name,
            max_price=max_price,
            number_of_servings=number_of_servings,
            base_mix_id=base_mix_id,
            base_mix_info=base_mix_info,
            add_mix_ids=add_mix_ids or [],
            ingredients=ingredients or []
        )

        # Call production API
        print(f"🔧 [BLEND TOOL] Calling production API: {PRODUCTION_API_URL}", file=sys.stderr)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PRODUCTION_API_URL,
                json=api_request,
                headers={"Content-Type": "application/json"}
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse response
            api_response = response.json()
            print(f"✅ [BLEND TOOL] Blend created successfully!", file=sys.stderr)
            print(f"✅ [BLEND TOOL] Product URL: {api_response.get('URLForBlend', 'N/A')}", file=sys.stderr)

            # Format response for AI agent
            return _format_response(api_response)

    except ValueError as e:
        # Invalid base_mix_id or other validation error
        error_msg = f"Validation error: {str(e)}"
        print(f"❌ [BLEND TOOL] {error_msg}", file=sys.stderr)
        return BlendCreationResponse(
            success=False,
            errors=[error_msg],
            blend_name=blend_name
        )

    except httpx.HTTPError as e:
        # API call failed
        error_msg = f"API error: {str(e)}"
        print(f"❌ [BLEND TOOL] {error_msg}", file=sys.stderr)
        return BlendCreationResponse(
            success=False,
            errors=[error_msg],
            blend_name=blend_name
        )

    except Exception as e:
        # Unexpected error
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ [BLEND TOOL] {error_msg}", file=sys.stderr)
        return BlendCreationResponse(
            success=False,
            errors=[error_msg],
            blend_name=blend_name
        )


# ============================================================================
# PRIVATE HELPER FUNCTIONS
# ============================================================================

def _build_api_request(
    user_first_name: str,
    user_last_name: str,
    user_email: str,
    user_gender: str,
    user_age: int,
    blend_description: str,
    formulation_notes: str,
    blend_name: str,
    max_price: float,
    number_of_servings: int,
    base_mix_id: int,
    base_mix_info: dict,
    add_mix_ids: List[int],
    ingredients: List[Dict]
) -> dict:
    """
    Build complete API request matching production schema.

    Constructs the exact JSON structure expected by the production API,
    including all required fields and proper data types.
    """

    # Generate UUIDs for event_id and key (as per instructions.txt)
    event_id = str(uuid.uuid4())
    key = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build profile object (using test profile ID)
    profile = {
        "id": TEST_PROFILE_ID,
        "firstName": user_first_name,
        "lastName": user_last_name,
        "email": TEST_PROFILE_EMAIL,  # Override with test email for safety
        "gender": user_gender,
        "age": str(user_age)  # API expects string
    }

    # Build blend information object
    blend_information = {
        "blendDescription": blend_description,
        "formulationNotes": formulation_notes,
        "blendName": blend_name,
        "blendType": "AI Generated",
        "blendCategory": "Personalized",
        "blendSubCategory": "AI Consultation",
        "maxPrice": max_price,
        "numberOfServings": number_of_servings,
        "blendFirstName": True,
        "blendLastName": True,
        "blendNameSuffix": "AI Blend",
        "sendCommunication": True,
        "senderAccount": DEFAULT_SENDER_ACCOUNT,
        "referrer": DEFAULT_REFERRER,
        "referrerExternalNumber": event_id,  # Use event_id as external reference
        "referrerExternalType": "AI_SESSION",
        "aiReportViewForward": True,
        "aiReportSendImmediately": False,
        "openAIFlag": True,  # Mark as AI-generated
        "createdAt": timestamp
    }

    # Build base mix object
    base_mix = {
        "baseMixId": base_mix_id,
        "baseMixType": base_mix_info["name"],
        "baseMixTypeId": base_mix_info["typeId"],
        "baseMixName": base_mix_info["name"]
    }

    # Build add-mixes array
    # Note: We only have add-mix IDs from AI, not the full metadata
    # API might accept just IDs or might need full objects
    # For now, create minimal objects with IDs only
    add_mixes = []
    # TODO: This needs proper mapping from add_mix_id to add_mix metadata
    # For now, leaving empty - AI can select from database later

    # Build ingredients array
    formatted_ingredients = []
    for ing in ingredients:
        # Convert Pydantic model to dict
        formatted_ingredients.append({
            "ingredientId": ing.ingredientId,
            "name": ing.name,
            "amount": ing.amount,
            "description": ing.description
        })

    # Build complete request
    request = {
        "event_id": event_id,
        "key": key,
        "template_id": TEMPLATE_ID,
        "profile": profile,
        "blendInformation": blend_information,
        "baseMix": base_mix,
        "addMixes": add_mixes,
        "ingredients": formatted_ingredients
    }

    return request


def _format_response(api_response: dict) -> BlendCreationResponse:
    """
    Format production API response for AI agent consumption.

    Extracts key information and structures it in a clean format
    that the AI can easily present to the user.
    """

    # Check if response indicates success
    success = api_response.get("success", False)
    errors = api_response.get("errors", [])

    # Extract blend information
    blend_info = api_response.get("blendInformation", {})
    nutritional_info = api_response.get("nutritionalInformation", {})

    return BlendCreationResponse(
        success=success,
        errors=errors,
        blend_url=api_response.get("URLForBlend", ""),
        product_image_url=api_response.get("ProductImagePath", ""),
        nutritional_label_url=api_response.get("NutritionalLabel", ""),
        blend_name=blend_info.get("BlendName", ""),
        price=blend_info.get("Price", 0.0),
        servings=blend_info.get("NumberOfServings", 0),
        base_mix=blend_info.get("BaseMix", ""),
        nutritional_info=NutritionalInfo(
            calories=nutritional_info.get("calories", 0),
            protein=nutritional_info.get("protein", 0.0),
            carbohydrates=nutritional_info.get("carbohydrates", 0.0),
            fats=nutritional_info.get("fats", 0.0),
            fiber=nutritional_info.get("fiber", 0.0),
            energy=nutritional_info.get("energy", 0.0)
        ),
        ingredients=api_response.get("ingredients", []),
        add_mixes=api_response.get("addMixes", [])
    )
