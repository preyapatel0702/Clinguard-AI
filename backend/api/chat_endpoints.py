"""
chat_endpoints.py
------------------
Compatibility layer: POST /chat/messages

The frontend Chat client calls POST /chat/messages, but the backend's core
safety pipeline is exposed via POST /analyze (see backend.api.endpoints).
Rather than duplicating pipeline logic, this router:

  1. Accepts a chat-shaped request (ChatRequest).
  2. Converts it into an AnalyzeRequest.
  3. Runs it through the existing, unmodified ClinGuardPipeline instance.
  4. Maps the resulting AnalyzeResponse back into a chat-shaped ChatResponse,
     returning the safe/sanitized text as the assistant's reply.

/analyze itself is untouched — this module only adds a new route.
"""

import uuid

from fastapi import APIRouter, HTTPException

from backend.models.schemas import AnalyzeRequest
from backend.models.chat_schemas import ChatRequest, ChatResponse
from backend.api.endpoints import pipeline  # reuse the existing ClinGuardPipeline instance
from backend.agents.generator_agent.response_generator import DraftResponseGenerator

router = APIRouter()

# Produces the initial, not-yet-safety-reviewed clinical draft for a user's
# query (stand-in for an upstream LLM call). The pipeline below remains
# solely responsible for safety review of that draft.
_draft_generator = DraftResponseGenerator()


def _extract_message_text(request: ChatRequest) -> str:
    """Pull the text to analyze out of either `messages` or `message`."""
    if request.messages:
        # Use the most recent user-authored message; fall back to the last message overall.
        user_messages = [m for m in request.messages if m.role == "user"]
        chosen = (user_messages[-1] if user_messages else request.messages[-1])
        if chosen.content and chosen.content.strip():
            return chosen.content

    if request.message and request.message.strip():
        return request.message

    raise HTTPException(
        status_code=422,
        detail="ChatRequest must include a non-empty `message` or `messages` list.",
    )


def _to_analyze_request(request: ChatRequest) -> AnalyzeRequest:
    text = _extract_message_text(request)
    patient_id = request.patient_id or request.session_id or f"chat-{uuid.uuid4().hex[:8]}"

    # Bug fix: this previously set ai_response=text, i.e. it fed the user's
    # own question back into the pipeline as if it were the AI's answer.
    # Since the question itself rarely contains dangerous phrasing, the
    # safety pipeline had nothing to rewrite, so LOW/MODERATE risk replies
    # ended up being just the echoed question plus the disclaimer.
    # A real (drafted) clinical response must be generated first; the
    # pipeline's job is to safety-review that draft, not to author it.
    draft_response = _draft_generator.generate(text)

    return AnalyzeRequest(
        patient_id=patient_id,
        query=text,
        ai_response=draft_response,
        patient_age=request.patient_age,
        comorbidities=request.comorbidities,
    )


@router.post("/chat/messages", response_model=ChatResponse)
async def post_chat_messages(request: ChatRequest):
    """
    Compatibility endpoint for the frontend Chat client.

    Converts the chat request into an AnalyzeRequest, runs it through the
    existing ClinGuardPipeline (identical to /analyze), and returns the
    assistant's reply derived from AnalyzeResponse.safe_response.
    """
    analyze_request = _to_analyze_request(request)

    try:
        analyze_response = pipeline.run(analyze_request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(exc)}",
        )

    return ChatResponse(
        role="assistant",
        reply=analyze_response.safe_response,
        session_id=request.session_id,
        risk_level=analyze_response.risk_level,
        risk_score=analyze_response.risk_score,
        alerts=[alert.model_dump() for alert in analyze_response.alerts],
        analysis=analyze_response.model_dump(),
    )