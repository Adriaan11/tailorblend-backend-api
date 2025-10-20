#!/usr/bin/env python3
"""
TailorBlend AI Consultant - FastAPI Backend

Minimal API for OpenAI Agents SDK integration with Blazor frontend.
Provides SSE streaming for real-time chat responses.

Endpoints:
- GET  /api/health                 - Health check
- GET  /api/chat/stream            - Stream chat response (SSE)
- GET  /api/session/stats          - Get session statistics
- GET  /api/instructions           - Get current instructions
- POST /api/instructions           - Update instructions
- POST /api/session/reset          - Reset session state
"""

import asyncio
import sys
import json
import mimetypes
import logging
from typing import Optional, Dict, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ============================================================================
# Startup Logging Configuration
# ============================================================================
# Configure detailed logging for debugging startup issues
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)-8s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("🚀 STARTUP: Initializing TailorBlend Backend API")

# Import existing agent logic
# Add parent directory to path for both local and Docker
import os

# Log important environment variables
logger.info("=" * 80)
logger.info("📊 Environment Configuration:")
logger.info(f"   PYTHON_API_PORT: {os.getenv('PYTHON_API_PORT', 'NOT_SET')}")
logger.info(f"   CORS_ALLOWED_ORIGINS: {os.getenv('CORS_ALLOWED_ORIGINS', 'NOT_SET')}")
logger.info(f"   RAILWAY_PUBLIC_DOMAIN: {os.getenv('RAILWAY_PUBLIC_DOMAIN', 'NOT_SET')}")
logger.info(f"   RAILWAY_SERVICE_NAME: {os.getenv('RAILWAY_SERVICE_NAME', 'NOT_SET')}")
logger.info(f"   ASPNETCORE_ENVIRONMENT: {os.getenv('ASPNETCORE_ENVIRONMENT', 'NOT_SET')}")
logger.info("=" * 80)

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger.debug(f"📂 Parent directory: {parent_dir}")
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    logger.debug(f"✅ Added parent directory to sys.path")

logger.info("📦 Loading imports...")
try:
    logger.debug("→ Importing tb_agents.consultant")
    from tb_agents.consultant import create_tailorblend_consultant
    logger.debug("✅ tb_agents.consultant imported")
except Exception as e:
    logger.error(f"❌ Failed to import tb_agents.consultant: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing tb_agents.multi_agent_orchestrator")
    from tb_agents.multi_agent_orchestrator import MultiAgentOrchestrator
    logger.debug("✅ tb_agents.multi_agent_orchestrator imported")
except Exception as e:
    logger.error(f"❌ Failed to import MultiAgentOrchestrator: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing config.settings")
    from config.settings import load_instructions, load_practitioner_instructions, OPENAI_API_KEY
    logger.debug("✅ config.settings imported")
    logger.info(f"✓ OPENAI_API_KEY loaded (first 10 chars: {OPENAI_API_KEY[:10]}...)")
except Exception as e:
    logger.error(f"❌ Failed to import config.settings: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing agents.Runner, RunConfig, ModelSettings")
    from agents import Runner, RunConfig, ModelSettings
    from openai.types.shared import Reasoning
    logger.debug("✅ agents.Runner, RunConfig, ModelSettings imported")
except Exception as e:
    logger.error(f"❌ Failed to import agents modules: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing agents.tracing")
    from agents.tracing import add_trace_processor
    logger.debug("✅ agents.tracing imported")
except Exception as e:
    logger.error(f"❌ Failed to import agents.tracing: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing trace_processor")
    from backend.trace_processor import trace_processor
    logger.debug("✅ trace_processor imported")
except Exception as e:
    logger.error(f"❌ Failed to import trace_processor: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing openai.types.responses")
    from openai.types.responses import ResponseTextDeltaEvent
    logger.debug("✅ openai.types.responses imported")
except Exception as e:
    logger.error(f"❌ Failed to import ResponseTextDeltaEvent: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing instruction_parser")
    from instruction_parser import parse_instructions, reassemble_instructions
    logger.debug("✅ instruction_parser imported")
except Exception as e:
    logger.error(f"❌ Failed to import instruction_parser: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing token_counter")
    from token_counter import calculate_cost_zar
    logger.debug("✅ token_counter imported")
except Exception as e:
    logger.error(f"❌ Failed to import token_counter: {e}", exc_info=True)
    raise

try:
    logger.debug("→ Importing backend.models")
    from backend.models import MultiAgentBlendRequest, AgentStep
    logger.debug("✅ backend.models imported")
except Exception as e:
    logger.error(f"❌ Failed to import backend.models: {e}", exc_info=True)
    raise

logger.info("✅ All imports successful")

# CRITICAL: Set OpenAI API key in environment for the Agents SDK
logger.info("🔑 Setting OPENAI_API_KEY environment variable")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
logger.info("✅ OPENAI_API_KEY set in environment")

# ============================================================================
# Data Models
# ============================================================================

class FileAttachment(BaseModel):
    """File attachment model for chat messages."""
    filename: str = Field(..., description="Original filename")
    base64_data: str = Field(..., description="Base64 encoded file content")
    mime_type: str = Field(..., description="MIME type (e.g., application/pdf, image/jpeg)")
    file_size: int = Field(..., description="File size in bytes")

class ChatRequest(BaseModel):
    """Chat request model with optional attachments."""
    message: str = Field(..., description="User message text")
    session_id: str = Field(..., description="Session identifier")
    custom_instructions: Optional[str] = Field(None, description="Custom instructions override")
    model: str = Field("gpt-4.1-mini-2025-04-14", description="OpenAI model to use")
    attachments: List[FileAttachment] = Field(default_factory=list, description="File attachments")
    practitioner_mode: bool = Field(False, description="Use practitioner-specific instructions")
    reasoning_effort: Optional[str] = Field("minimal", description="Reasoning effort for GPT-5 models (minimal/low/medium/high)")
    verbosity: Optional[str] = Field("medium", description="Response verbosity for GPT-5 models (low/medium/high)")


class TokenInfo(BaseModel):
    """Token usage information for a chat response."""
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    total_tokens: int = Field(..., description="Total tokens used")


class ChatResponse(BaseModel):
    """Non-streaming chat response (complete response returned at once)."""
    response: str = Field(..., description="Complete AI response text")
    session_id: str = Field(..., description="Session identifier")
    tokens: TokenInfo = Field(..., description="Token usage statistics")
    cost_zar: float = Field(..., description="Cost in South African Rand")
    model: str = Field(..., description="OpenAI model used")
    message_count: int = Field(..., description="Total messages in this session")


# ============================================================================
# Utility Functions
# ============================================================================

def detect_mime_type(filename: str) -> str:
    """
    Detect MIME type from filename extension.

    Args:
        filename: Original filename with extension

    Returns:
        str: MIME type (e.g., 'application/pdf', 'image/jpeg')
    """
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type

    # Fallback mappings for common types
    ext_lower = filename.lower().split('.')[-1]
    fallback_types = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'txt': 'text/plain',
        'csv': 'text/csv',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    return fallback_types.get(ext_lower, 'application/octet-stream')

def build_message_content(message: str, attachments: List[FileAttachment]) -> List[Dict]:
    """
    Build OpenAI Agents SDK message content list from text + attachments.

    Args:
        message: User message text
        attachments: List of file attachments

    Returns:
        List of content items for SDK
    """
    content_items = []

    # Add attachments first
    for attachment in attachments:
        mime_type = attachment.mime_type

        # Determine if this is an image or generic file
        if mime_type.startswith('image/'):
            # Image attachment (uses input_image type)
            content_items.append({
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{attachment.base64_data}",
                "detail": "auto"
            })
            print(f"📎 [API] Added image attachment: {attachment.filename} ({mime_type})", file=sys.stderr)
        else:
            # Generic file attachment (uses input_file type)
            content_items.append({
                "type": "input_file",
                "file_data": f"data:{mime_type};base64,{attachment.base64_data}",
                "filename": attachment.filename
            })
            print(f"📎 [API] Added file attachment: {attachment.filename} ({mime_type})", file=sys.stderr)

    # Add text message last
    content_items.append({
        "type": "input_text",
        "text": message
    })

    return content_items

# ============================================================================
# Readiness State (for distinguishing liveness vs readiness probes)
# ============================================================================

# Liveness probe (/api/health): Always 200 after startup event
# Readiness probe (/api/ready): Only 200 after warm-up complete
is_ready = False

# ============================================================================
# Background Initialization (Heavy Operations)
# ============================================================================

async def _heavy_init():
    """
    Background task for heavy initialization that must NOT block startup.

    This includes:
    - MultiAgentOrchestrator initialization
    - TracingProcessor registration
    - Any other expensive setup

    Called via asyncio.create_task() to run in background.
    """
    global multi_agent_orchestrator, is_ready

    try:
        logger.info("🔄 [BACKGROUND] Starting heavy initialization...")

        # Register trace processor globally
        logger.info("📊 [BACKGROUND] Registering trace processor...")
        add_trace_processor(trace_processor)
        logger.info("✅ [BACKGROUND] Trace processor registered")

        logger.info("🤖 [BACKGROUND] Initializing MultiAgentOrchestrator...")

        # This is the expensive operation that was blocking startup
        multi_agent_orchestrator = MultiAgentOrchestrator()

        logger.info("✅ [BACKGROUND] MultiAgentOrchestrator initialized successfully")
        logger.info("✅ [BACKGROUND] Heavy initialization complete")

        # Now mark as ready
        is_ready = True
        logger.info("🎉 [BACKGROUND] Application is now READY for full requests")

    except Exception as e:
        logger.error(f"❌ [BACKGROUND] Failed to initialize: {e}", exc_info=True)
        # Don't raise - app can still serve health checks
        # is_ready stays False, so /api/ready will return 503

# ============================================================================
# Lifespan Context Manager (Non-Blocking Startup)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for non-blocking startup.

    Key pattern: Kick off heavy init in background via asyncio.create_task(),
    then IMMEDIATELY yield so uvicorn stops returning 503.

    Railway health checks will succeed because /health returns 200
    even while initialization runs in the background.
    """
    logger.info("=" * 80)
    logger.info("🚀 LIFESPAN: FastAPI startup initiated")
    logger.info("=" * 80)

    # Schedule heavy init in background - DO NOT AWAIT IT!
    asyncio.create_task(_heavy_init())

    logger.info("✅ LIFESPAN: Background initialization scheduled")
    logger.info("✅ LIFESPAN: Startup complete (non-blocking)")

    # Debug: Print all registered routes
    logger.info("📋 REGISTERED ROUTES:")
    for route in app.routes:
        try:
            path = getattr(route, 'path', 'N/A')
            methods = getattr(route, 'methods', 'N/A')
            logger.info(f"   → {path} {methods}")
        except Exception as e:
            logger.debug(f"   → Route info unavailable: {e}")

    logger.info("=" * 80)

    # Yield immediately - uvicorn will stop returning 503
    yield

    # Teardown (if needed)
    logger.info("🛑 LIFESPAN: Shutdown initiated")
    logger.info("=" * 80)

# ============================================================================
# Application Setup
# ============================================================================

logger.info("🏗️  Creating FastAPI application with lifespan...")
app = FastAPI(
    title="TailorBlend AI Consultant API",
    description="Backend API for OpenAI Agents SDK integration",
    version="1.0.0",
    lifespan=lifespan  # Non-blocking startup!
)
logger.info("✅ FastAPI application created")

# ============================================================================
# CORS Configuration - Supports local dev and multiple production deployments
# ============================================================================

logger.info("🔒 Configuring CORS...")
# Default allowed origins (local development)
allowed_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# Add production frontend origin from environment variable (optional)
# Set CORS_ALLOWED_ORIGINS environment variable for production:
# e.g., "https://ui.tailorblend.com,https://app.tailorblend.com"
cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_env:
    cors_origins_list = [origin.strip() for origin in cors_env.split(",")]
    allowed_origins.extend(cors_origins_list)
    logger.info(f"🔧 [CORS] Added {len(cors_origins_list)} production origin(s): {cors_origins_list}")
else:
    logger.debug("ℹ️  No CORS_ALLOWED_ORIGINS environment variable set")

logger.info(f"✅ [CORS] Allowed origins: {allowed_origins}")

try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("✅ CORS middleware added")
except Exception as e:
    logger.error(f"❌ Failed to add CORS middleware: {e}", exc_info=True)
    raise

# ============================================================================
# State Management
# ============================================================================

logger.info("📊 Initializing state management...")
# Global conversation state (keyed by session_id)
# Structure: {session_id: {previous_response_id, message_count, tokens, ...}}
conversation_state: Dict[str, Dict] = {}
logger.debug("✅ conversation_state initialized")

# Custom instructions cache (keyed by session_id or "default")
# NOTE: In-memory only - resets on API restart. This is intentional.
# To permanently change instructions, edit spec/instructions.txt
custom_instructions_cache: Dict[str, str] = {}
logger.debug("✅ custom_instructions_cache initialized")

# Multi-agent session state (keyed by session_id)
# Separate from conversation_state to keep multi-agent system isolated
multi_agent_state: Dict[str, Dict] = {}
logger.debug("✅ multi_agent_state initialized")

# Multi-agent orchestrator instance (singleton)
# NOTE: Initialized in background during lifespan startup (non-blocking!)
multi_agent_orchestrator: Optional[MultiAgentOrchestrator] = None
logger.debug("✅ multi_agent_orchestrator placeholder created (will init in background)")

logger.info("✅ State management initialized")

# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health")
def health():
    """
    Root-level health check for Railway liveness probe.
    MUST be ultra-fast and ALWAYS return 200.
    No dependencies, no checks - purely confirms process is alive.
    """
    return {"status": "ok"}


@app.get("/ping")
def ping():
    """
    Ultra-simple synchronous ping endpoint for debugging routing.
    No async, no complex logic - just returns immediately.
    """
    return {"pong": "ok"}


@app.get("/")
def root():
    """
    Root endpoint for basic connectivity check.
    """
    logger.info("📍 ROOT endpoint called")
    return {
        "service": "TailorBlend AI Consultant API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/api/health")
def health_check():
    """
    Liveness probe - MUST return 200 immediately after startup.
    This is called by Railway/Docker to ensure app is alive.
    No dependencies checked - purely confirms the process is running.

    Returns:
        dict: Simple status
    """
    # Ultra-fast response - no logic, no checks
    return {"status": "ok"}


@app.get("/api/ready")
def readiness_check():
    """
    Readiness probe - Returns 200 only when app is fully warm and ready for requests.
    Use this for sophisticated load balancers/orchestrators.
    Railway uses /api/health (liveness), not this endpoint.

    Returns:
        dict: Ready status and details
    """
    global is_ready
    if not is_ready:
        return {"ready": False, "status": "warming up"}, 503

    return {
        "ready": True,
        "status": "ready for requests",
        "service": "tailorblend-ai-consultant-api",
        "version": "1.0.0"
    }


async def generate_chat_stream(
    message: str,
    session_id: str,
    custom_instructions: Optional[str] = None,
    model: str = "gpt-4.1-mini-2025-04-14",
    attachments: List[FileAttachment] = [],
    practitioner_mode: bool = False,
    reasoning_effort: Optional[str] = "minimal",
    verbosity: Optional[str] = "medium",
    request: Optional[Request] = None
):
    """
    Core chat streaming logic (shared between GET and POST endpoints).

    Generates SSE events for streaming response.

    Args:
        message: User message text
        session_id: Session identifier
        custom_instructions: Optional custom instructions
        model: OpenAI model to use
        attachments: List of file attachments
        practitioner_mode: Use practitioner-specific instructions if True

    Yields:
        str: SSE formatted messages ("data: {token}\n\n")
    """
    try:
        # Determine which instructions to use
        instructions_to_use = custom_instructions

        if instructions_to_use is None:
            # Load appropriate instructions based on mode
            if practitioner_mode:
                instructions_to_use = load_practitioner_instructions()
                print(f"🩺 [API] Using practitioner instructions for chat ({len(instructions_to_use)} chars)", file=sys.stderr)
            elif "default" in custom_instructions_cache:
                instructions_to_use = custom_instructions_cache["default"]
                print(f"✨ [API] Using cached custom instructions for chat ({len(instructions_to_use)} chars)", file=sys.stderr)
            else:
                print(f"📋 [API] Using default consumer instructions for chat", file=sys.stderr)
        else:
            print(f"✨ [API] Using explicit custom instructions for chat ({len(instructions_to_use)} chars)", file=sys.stderr)

        # Create agent with custom instructions and selected model
        # For GPT-5 models, add reasoning and verbosity settings
        is_gpt5 = model.startswith("gpt-5")

        if is_gpt5:
            print(f"🧠 [API] GPT-5 detected - using reasoning={reasoning_effort}, verbosity={verbosity}", file=sys.stderr)
            model_settings = ModelSettings(
                reasoning=Reasoning(effort=reasoning_effort),
                verbosity=verbosity
            )
            agent = create_tailorblend_consultant(
                custom_instructions=instructions_to_use,
                model=model,
                model_settings=model_settings
            )
        else:
            # GPT-4.x models - no special settings needed
            agent = create_tailorblend_consultant(
                custom_instructions=instructions_to_use,
                model=model
            )

        # Create RunConfig
        run_config = RunConfig(workflow_name="TailorBlend Consultation")

        # Get conversation context
        previous_response_id = None
        is_first_message = session_id not in conversation_state

        if session_id in conversation_state:
            previous_response_id = conversation_state[session_id].get("previous_response_id")

        # Inject hidden formatting instruction on first message
        # This tells the AI to always use markdown while staying conversational
        actual_message = message
        if is_first_message:
            hidden_instruction = (
                "[SYSTEM INSTRUCTION: Always format your responses using markdown syntax "
                "(use **bold** for important terms like supplement names, use bullet lists "
                "for recommendations, use numbered lists for steps, use headers for sections). "
                "Stay warm and conversational, but structure your responses with markdown. "
                "This makes your responses clearer and more professional.]\n\n"
            )
            actual_message = hidden_instruction + message
            print(f"✨ [FORMATTING] Injected markdown instruction for first message", file=sys.stderr)

        # Determine message format based on attachments
        if attachments:
            try:
                print(f"📎 [API] Building message with {len(attachments)} attachment(s)", file=sys.stderr)
                # Build message list with attachments for SDK
                message_content = build_message_content(actual_message, attachments)
                print(f"📎 [API] Built {len(message_content)} content items", file=sys.stderr)

                message_list = [
                    {
                        "role": "user",
                        "content": message_content
                    }
                ]

                # GPT-5 requires verified org for streaming, use non-streaming mode
                if is_gpt5:
                    print(f"💬 [API] GPT-5 detected - using non-streaming mode", file=sys.stderr)
                    result = Runner.run(
                        agent,
                        message_list,
                        previous_response_id=previous_response_id,
                        run_config=run_config
                    )
                    print(f"✅ [API] Runner.run completed successfully", file=sys.stderr)
                else:
                    print(f"📎 [API] Message list created, starting streaming...", file=sys.stderr)
                    result = Runner.run_streamed(
                        agent,
                        message_list,
                        previous_response_id=previous_response_id,
                        run_config=run_config
                    )
                    print(f"✅ [API] Runner.run_streamed initiated successfully", file=sys.stderr)

                # Associate trace with session for tracing
                if hasattr(result, 'trace_id'):
                    trace_processor.set_session_id(result.trace_id, session_id)
                    print(f"📊 [TRACE] Associated trace {result.trace_id} with session {session_id}", file=sys.stderr)

            except Exception as e:
                print(f"❌ [API] Error building/running message with attachments: {type(e).__name__}: {str(e)}", file=sys.stderr)
                import traceback
                print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
                raise
        else:
            # Simple string message (backward compatible)
            # GPT-5 requires verified org for streaming, use non-streaming mode
            if is_gpt5:
                print(f"💬 [API] GPT-5 detected - using non-streaming mode", file=sys.stderr)
                result = Runner.run(
                    agent,
                    actual_message,
                    previous_response_id=previous_response_id,
                    run_config=run_config
                )
                print(f"✅ [API] Runner.run completed successfully", file=sys.stderr)
            else:
                print(f"💬 [API] Sending text-only message", file=sys.stderr)
                result = Runner.run_streamed(
                    agent,
                    actual_message,
                    previous_response_id=previous_response_id,
                    run_config=run_config
                )

            # Associate trace with session for tracing
            if hasattr(result, 'trace_id'):
                trace_processor.set_session_id(result.trace_id, session_id)
                print(f"📊 [TRACE] Associated trace {result.trace_id} with session {session_id}", file=sys.stderr)

        # Accumulate response for token counting
        accumulated_response = ""

        # Track time for keepalive mechanism
        from datetime import datetime
        last_keepalive = datetime.now()

        # Handle streaming vs non-streaming responses
        if is_gpt5:
            # GPT-5 non-streaming: Send complete response at once
            print(f"📤 [API] Sending GPT-5 non-streaming response", file=sys.stderr)
            # Get the complete response text
            accumulated_response = result.text

            # Simulate streaming by yielding the complete response
            # This maintains compatibility with frontend expecting SSE stream
            yield f"data: {json.dumps(accumulated_response)}\n\n"
        else:
            # GPT-4 streaming: Send tokens as they arrive
            async for event in result.stream_events():
                # Check if client has disconnected (early termination)
                if request and await request.is_disconnected():
                    print(f"🔌 [API] Client disconnected for session {session_id}, stopping stream", file=sys.stderr)
                    break

                # Send keepalive if no activity for 15 seconds
                # This prevents fly.io proxy from closing idle connections
                if (datetime.now() - last_keepalive).total_seconds() > 15:
                    yield f": keepalive\n\n"  # SSE comment (ignored by clients)
                    last_keepalive = datetime.now()

                if (
                    event.type == "raw_response_event" and
                    isinstance(event.data, ResponseTextDeltaEvent)
                ):
                    token = event.data.delta
                    accumulated_response += token

                    # Send SSE event
                    yield f"data: {json.dumps(token)}\n\n"

                    # Reset keepalive timer on activity
                    last_keepalive = datetime.now()

        # Store conversation state
        if session_id not in conversation_state:
            conversation_state[session_id] = {
                "message_count": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "model": model
            }

        conversation_state[session_id]["previous_response_id"] = result.last_response_id
        conversation_state[session_id]["message_count"] += 1
        conversation_state[session_id]["model"] = model  # Update model for this session

        # Debug: Log result attributes
        print(f"🔍 [DEBUG] Result type: {type(result)}", file=sys.stderr)
        print(f"🔍 [DEBUG] Result attributes: {dir(result)}", file=sys.stderr)
        print(f"🔍 [DEBUG] Has usage attr: {hasattr(result, 'usage')}", file=sys.stderr)
        if hasattr(result, 'usage'):
            print(f"🔍 [DEBUG] Usage value: {result.usage}", file=sys.stderr)

        # Track actual usage if available
        if hasattr(result, 'usage') and result.usage:
            conversation_state[session_id]["total_input_tokens"] += result.usage.input_tokens
            conversation_state[session_id]["total_output_tokens"] += result.usage.output_tokens
            conversation_state[session_id]["last_usage"] = {
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "total_tokens": result.usage.total_tokens
            }
        else:
            # Fallback: estimate tokens
            print(f"⚠️ [DEBUG] Using estimation fallback (no usage data)", file=sys.stderr)
            from token_counter import count_tokens

            # Load actual instructions if custom_instructions is None
            if custom_instructions:
                instructions_to_count = custom_instructions
            else:
                instructions_to_count = load_instructions()

            estimated_input = count_tokens(instructions_to_count) + count_tokens(message)
            estimated_output = count_tokens(accumulated_response)

            print(f"📊 [DEBUG] Estimated input tokens: {estimated_input}", file=sys.stderr)
            print(f"📊 [DEBUG] Estimated output tokens: {estimated_output}", file=sys.stderr)

            conversation_state[session_id]["total_input_tokens"] += estimated_input
            conversation_state[session_id]["total_output_tokens"] += estimated_output

        # Send completion event
        yield f"data: [DONE]\n\n"

    except Exception as e:
        # Send error event
        error_message = f"Error: {str(e)}"
        print(f"❌ [API] Streaming error: {error_message}", file=sys.stderr)

        # Sanitize error message - don't expose internal details to users
        user_error_message = "We're having trouble processing your request. Please try again in a moment."
        yield f"data: {json.dumps(user_error_message)}\n\n"

        # CRITICAL: Always send [DONE] signal, even after errors
        # This ensures the frontend knows the stream has terminated
        yield f"data: [DONE]\n\n"


@app.post("/api/chat")
async def chat_post(chat_request: ChatRequest, request: Request):
    """
    Non-streaming chat endpoint.

    Collects full OpenAI response internally, then returns complete JSON.
    Frontend simulates streaming for better UX.

    Advantages over SSE:
    - No HTTP/2 protocol errors
    - No CORS complexity
    - Simple retry logic
    - Works with any proxy/CDN

    Args:
        chat_request: Chat request with message and optional attachments
        request: FastAPI Request object (for disconnect detection)

    Returns:
        ChatResponse: Complete response with tokens and cost
    """
    try:
        print(f"📨 [POST /api/chat] Received non-streaming request", file=sys.stderr)
        print(f"  - Message: {chat_request.message[:50]}..." if len(chat_request.message) > 50 else f"  - Message: {chat_request.message}", file=sys.stderr)
        print(f"  - Session: {chat_request.session_id}", file=sys.stderr)
        print(f"  - Attachments: {len(chat_request.attachments)}", file=sys.stderr)

        # Accumulate full response from streaming generator
        full_response = ""

        # Add timeout to prevent hanging forever
        import asyncio
        timeout_seconds = 120  # 2 minutes max

        try:
            # Use existing generate_chat_stream but consume internally with timeout
            async def consume_stream():
                nonlocal full_response
                chunk_count = 0
                async for chunk in generate_chat_stream(
                    chat_request.message,
                    chat_request.session_id,
                    chat_request.custom_instructions,
                    chat_request.model,
                    chat_request.attachments,
                    chat_request.practitioner_mode,
                    chat_request.reasoning_effort,
                    chat_request.verbosity,
                    request=request
                ):
                    chunk_count += 1
                    if chunk_count == 1:
                        print(f"✅ [POST /api/chat] Received first chunk from stream", file=sys.stderr)

                    # Skip SSE formatting - only accumulate actual content
                    # generate_chat_stream yields strings like "data: \"token\"\n\n"
                    if isinstance(chunk, str):
                        # Extract token from SSE format: "data: \"token\"\n\n" → "token"
                        if chunk.startswith("data: "):
                            data_content = chunk[6:].strip()
                            if data_content and data_content != "[DONE]":
                                # Parse JSON token
                                try:
                                    import json
                                    token = json.loads(data_content)
                                    full_response += token
                                except json.JSONDecodeError:
                                    # Not JSON, use raw content
                                    full_response += data_content

                print(f"✅ [POST /api/chat] Stream complete, received {chunk_count} chunks", file=sys.stderr)

            print(f"⏳ [POST /api/chat] Starting stream consumption with {timeout_seconds}s timeout...", file=sys.stderr)
            await asyncio.wait_for(consume_stream(), timeout=timeout_seconds)
            print(f"✅ [POST /api/chat] Stream consumed successfully", file=sys.stderr)

        except asyncio.TimeoutError:
            print(f"⏱️ [POST /api/chat] Timeout after {timeout_seconds}s, returning partial response", file=sys.stderr)
            if not full_response:
                raise HTTPException(status_code=504, detail=f"Request timed out after {timeout_seconds} seconds")
        except Exception as stream_error:
            print(f"❌ [POST /api/chat] Error in stream consumption: {type(stream_error).__name__}: {stream_error}", file=sys.stderr)
            import traceback
            print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
            raise

        # Get session state for token tracking
        session_state = conversation_state.get(chat_request.session_id, {})

        # Extract token info from last_usage (set by generate_chat_stream)
        if "last_usage" in session_state:
            usage = session_state["last_usage"]
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
        else:
            # Fallback: estimate tokens
            print(f"⚠️ [POST /api/chat] No usage data, estimating...", file=sys.stderr)
            from token_counter import count_tokens
            input_tokens = count_tokens(chat_request.message)
            output_tokens = count_tokens(full_response)

        # Calculate cost in ZAR
        from token_counter import calculate_cost_zar
        cost_info = calculate_cost_zar(input_tokens, output_tokens)

        # Build response
        response = ChatResponse(
            response=full_response,
            session_id=chat_request.session_id,
            tokens=TokenInfo(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens
            ),
            cost_zar=cost_info["total_cost_zar"],
            model=chat_request.model,
            message_count=session_state.get("message_count", 1)
        )

        print(f"✅ [POST /api/chat] Response ready: {len(full_response)} chars", file=sys.stderr)
        print(f"📊 Tokens: {input_tokens} in / {output_tokens} out", file=sys.stderr)
        print(f"💰 Cost: R{cost_info['total_cost_zar']:.4f}", file=sys.stderr)

        return response

    except Exception as e:
        print(f"❌ [POST /api/chat] Error: {e}", file=sys.stderr)
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/stream")
async def stream_chat_get(
    request: Request,
    message: str = Query(..., description="User message"),
    session_id: str = Query(..., description="Session identifier"),
    custom_instructions: Optional[str] = Query(None, description="Custom instructions override"),
    model: str = Query("gpt-4.1-mini-2025-04-14", description="OpenAI model to use")
):
    """
    Stream chat response using Server-Sent Events (SSE) - GET endpoint.

    This endpoint supports text-only messages for backward compatibility.
    For messages with file attachments, use the POST endpoint.

    Args:
        request: FastAPI Request object (for disconnect detection)
        message: User's message
        session_id: Session identifier for conversation continuity
        custom_instructions: Optional custom instructions from Configuration editor
        model: OpenAI model to use (defaults to gpt-4.1-mini-2025-04-14)

    Returns:
        StreamingResponse: SSE stream of response tokens
    """
    return StreamingResponse(
        generate_chat_stream(message, session_id, custom_instructions, model, [], request=request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Transfer-Encoding": "chunked"  # Explicit chunked encoding for fly.io SSE
        }
    )


@app.post("/api/chat/stream")
async def stream_chat_post(chat_request: ChatRequest, request: Request):
    """
    Stream chat response using Server-Sent Events (SSE) - POST endpoint.

    This endpoint supports messages with file attachments.
    Accepts JSON body with message, session_id, and optional attachments.

    Args:
        chat_request: Chat request with message and optional attachments
        request: FastAPI Request object (for disconnect detection)

    Returns:
        StreamingResponse: SSE stream of response tokens
    """
    try:
        # Log incoming request details
        print(f"📨 [POST /api/chat/stream] Received request:", file=sys.stderr)
        print(f"  - Message: {chat_request.message[:50]}..." if len(chat_request.message) > 50 else f"  - Message: {chat_request.message}", file=sys.stderr)
        print(f"  - Session ID: {chat_request.session_id}", file=sys.stderr)
        print(f"  - Model: {chat_request.model}", file=sys.stderr)
        print(f"  - Attachments: {len(chat_request.attachments)} file(s)", file=sys.stderr)

        for i, attachment in enumerate(chat_request.attachments):
            print(f"    [{i+1}] {attachment.filename} ({attachment.mime_type}, {attachment.file_size} bytes)", file=sys.stderr)
            print(f"        Base64 data length: {len(attachment.base64_data)} chars", file=sys.stderr)

        return StreamingResponse(
            generate_chat_stream(
                chat_request.message,
                chat_request.session_id,
                chat_request.custom_instructions,
                chat_request.model,
                chat_request.attachments,
                chat_request.practitioner_mode,
                chat_request.reasoning_effort,
                chat_request.verbosity,
                request=request
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Transfer-Encoding": "chunked"  # Explicit chunked encoding for fly.io SSE
            }
        )
    except Exception as e:
        print(f"❌ [POST /api/chat/stream] ERROR: {type(e).__name__}: {str(e)}", file=sys.stderr)
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
        raise


@app.get("/api/session/stats")
async def get_session_stats(session_id: str = Query(..., description="Session identifier")):
    """
    Get session statistics (message count, token usage, cost).

    Args:
        session_id: Session identifier

    Returns:
        dict: Session statistics including tokens and ZAR cost
    """
    print(f"📊 [STATS] Fetching stats for session: {session_id}", file=sys.stderr)
    print(f"📊 [STATS] Session exists in state: {session_id in conversation_state}", file=sys.stderr)

    if session_id not in conversation_state:
        print(f"⚠️ [STATS] Session not found, returning zeros", file=sys.stderr)
        return {
            "session_id": session_id,
            "message_count": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "cost_zar": 0.0,
            "cost_formatted": "R0.00"
        }

    stats = conversation_state[session_id]
    input_tokens = stats.get("total_input_tokens", 0)
    output_tokens = stats.get("total_output_tokens", 0)
    total_tokens = input_tokens + output_tokens
    model = stats.get("model", "gpt-4.1-mini-2025-04-14")

    print(f"📊 [STATS] Input tokens: {input_tokens}", file=sys.stderr)
    print(f"📊 [STATS] Output tokens: {output_tokens}", file=sys.stderr)
    print(f"📊 [STATS] Total tokens: {total_tokens}", file=sys.stderr)

    # Calculate cost in ZAR with model-specific pricing
    from token_counter import format_cost_zar
    cost_info = calculate_cost_zar(input_tokens, output_tokens, model=model)

    result = {
        "session_id": session_id,
        "model": model,
        "message_count": stats.get("message_count", 0),
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_zar": cost_info["total_cost_zar"],
        "cost_formatted": format_cost_zar(cost_info["total_cost_zar"])
    }

    print(f"✅ [STATS] Returning: {result}", file=sys.stderr)
    return result


@app.get("/api/instructions")
async def get_instructions():
    """
    Get current instructions (for Configuration editor).

    Returns custom instructions from cache if available,
    otherwise returns default instructions from disk.

    Returns:
        dict: Instructions parsed into sections
    """
    try:
        # Check cache first before loading from disk
        if "default" in custom_instructions_cache:
            instructions = custom_instructions_cache["default"]
            print(f"📖 [API] Returning cached custom instructions ({len(instructions)} chars)", file=sys.stderr)
        else:
            instructions = load_instructions()
            print(f"📖 [API] Returning default instructions from disk", file=sys.stderr)

        sections = parse_instructions(instructions)

        return {
            "success": True,
            "sections": sections,
            "full_text": instructions
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/instructions")
async def update_instructions(data: dict):
    """
    Update instructions from Configuration editor.

    Saves to both in-memory cache and persistent disk storage.

    Args:
        data: Dict with either:
              - "sections" key containing updated sections (granular mode)
              - "raw_text" key containing complete instructions (raw mode)

    Returns:
        dict: Success status
    """
    try:
        # Check if raw text mode
        if "raw_text" in data:
            instructions = data.get("raw_text", "")
            print(f"📝 [API] Updating RAW instructions ({len(instructions)} chars)", file=sys.stderr)
        else:
            # Granular sections mode
            sections = data.get("sections", {})
            instructions = reassemble_instructions(sections)
            print(f"📝 [API] Updating GRANULAR instructions ({len(sections)} sections)", file=sys.stderr)

        # Store in cache (in-memory only - resets on API restart)
        custom_instructions_cache["default"] = instructions
        print(f"💾 [API] Updated custom instructions in cache ({len(instructions)} chars)", file=sys.stderr)

        return {
            "success": True,
            "message": "Instructions updated successfully (session only - resets on API restart)"
        }
    except Exception as e:
        print(f"❌ [API] Failed to update instructions: {e}", file=sys.stderr)
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/instructions/reset")
async def reset_instructions():
    """
    Reset to default instructions (clear custom cache).

    Clears the in-memory custom instructions cache,
    returning to the default instructions from spec/instructions.txt.

    Returns:
        dict: Success status
    """
    try:
        # Clear in-memory cache
        if "default" in custom_instructions_cache:
            del custom_instructions_cache["default"]
            print(f"🔄 [API] Cleared custom instructions from cache", file=sys.stderr)
        else:
            print(f"ℹ️ [API] No custom instructions in cache to clear", file=sys.stderr)

        print(f"✅ [API] Reset to default instructions", file=sys.stderr)

        return {
            "success": True,
            "message": "Reset to default instructions (from spec/instructions.txt)"
        }
    except Exception as e:
        print(f"❌ [API] Failed to reset instructions: {e}", file=sys.stderr)
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/multi-agent/stream")
async def multi_agent_blend_stream(request: MultiAgentBlendRequest):
    """
    Multi-agent blend formulation with streaming progress.

    This endpoint uses a 2-agent system:
    1. Supplement Specialist - Selects ingredients and dosages
    2. Formulation Specialist - Configures base mix and delivery

    Args:
        request: Patient profile and health goals

    Returns:
        StreamingResponse: SSE stream of agent progress steps

    Example:
        POST /api/multi-agent/stream
        {
            "session_id": "abc123",
            "health_goals": "Better sleep and more energy",
            "age": 35,
            "dietary_preferences": "vegetarian"
        }
    """
    session_id = request.session_id

    print(f"\n{'='*80}", file=sys.stderr)
    print(f"🤖 [MULTI-AGENT] Starting formulation for session: {session_id}", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)

    async def event_generator():
        """Generate SSE events from multi-agent workflow."""
        try:
            # Check if orchestrator is initialized
            if multi_agent_orchestrator is None:
                error_step = AgentStep(
                    agent_name="System",
                    step_type="error",
                    content="Service is still warming up. Please try again in a moment."
                )
                yield f"data: {error_step.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Stream agent steps
            async for step in multi_agent_orchestrator.create_blend(request):
                # Convert AgentStep to JSON
                step_json = step.model_dump_json()

                # Yield as SSE event
                yield f"data: {step_json}\n\n"

                # Log progress
                print(f"📤 [{step.agent_name}] {step.step_type}: {step.content[:50]}...",
                      file=sys.stderr)

            # Send completion signal
            yield "data: [DONE]\n\n"
            print(f"\n✅ [MULTI-AGENT] Formulation complete for session: {session_id}\n",
                  file=sys.stderr)

        except Exception as e:
            # Stream error to client
            error_step = AgentStep(
                agent_name="System",
                step_type="error",
                content=f"Fatal error: {str(e)}"
            )
            yield f"data: {error_step.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

            print(f"\n❌ [MULTI-AGENT] Error in session {session_id}: {e}\n",
                  file=sys.stderr)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.get("/api/session/{session_id}/traces/stream")
async def stream_traces(session_id: str):
    """
    Stream trace updates via Server-Sent Events (SSE).

    Real-time streaming of trace data as consultations execute.
    Keeps connection open until client disconnects.

    Args:
        session_id: Session identifier

    Returns:
        StreamingResponse: SSE stream of trace events
    """
    print(f"📊 [TRACE-STREAM] Client connected for session: {session_id}", file=sys.stderr)

    async def event_generator():
        # Subscribe to trace updates
        queue = await trace_processor.subscribe_to_traces(session_id)

        try:
            while True:
                # Wait for next trace update
                trace_data = await queue.get()

                # Format as SSE event
                import json
                event_data = json.dumps(trace_data)
                yield f"data: {event_data}\n\n"

        except asyncio.CancelledError:
            print(f"📊 [TRACE-STREAM] Client disconnected for session: {session_id}", file=sys.stderr)
            # Unsubscribe from updates
            trace_processor.unsubscribe_from_traces(session_id, queue)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.get("/api/session/{session_id}/traces")
async def get_traces(session_id: str):
    """
    Get all traces for a session.

    Args:
        session_id: Session identifier

    Returns:
        dict: List of traces
    """
    traces = trace_processor.get_traces(session_id)

    return {
        "session_id": session_id,
        "traces": traces,
        "count": len(traces)
    }


@app.post("/api/session/reset")
async def reset_session(session_id: str = Form(..., description="Session identifier to reset")):
    """
    Reset session state (clear conversation history and traces).

    Args:
        session_id: Session identifier to reset (sent as form data)

    Returns:
        dict: Success status
    """
    print(f"🔄 [RESET] Resetting session: {session_id}", file=sys.stderr)

    if session_id in conversation_state:
        del conversation_state[session_id]
        print(f"✅ [RESET] Session {session_id} deleted from state", file=sys.stderr)
    else:
        print(f"⚠️ [RESET] Session {session_id} not found in state", file=sys.stderr)

    # Also clear traces
    trace_processor.clear_session(session_id)
    print(f"📊 [RESET] Traces cleared for session {session_id}", file=sys.stderr)

    return {
        "success": True,
        "message": f"Session {session_id} reset successfully"
    }


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """
    Main entry point for local development.

    NOTE: For Railway/Docker deployments, the Dockerfile CMD runs uvicorn directly:
      CMD ["/bin/sh", "-lc", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-5000} --workers 4"]

    For local development, run:
      uvicorn backend.api:app --host 0.0.0.0 --port 5000 --workers 4
      OR
      python -m backend.api (if this main() is called)
    """
    logger.info("=" * 80)
    logger.info("🚀 TAILORBLEND BACKEND API - LOCAL DEVELOPMENT")
    logger.info("=" * 80)
    logger.info("ℹ️  For production, uvicorn is started by Docker/Railway")
    logger.info("ℹ️  For local dev, consider running: uvicorn backend.api:app --reload")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
