"""API routes for the YouTube RAG application."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.transcript import TranscriptService
from app.services.rag_pipeline import RAGPipeline
from app.services.models import ModelService
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["rag"])

# ── Shared pipeline instance ────────────────────────────────────────────────
pipeline = RAGPipeline()


# ── Request / Response schemas ───────────────────────────────────────────────
class TranscriptRequest(BaseModel):
    video_url_or_id: str = Field(..., min_length=1, description="YouTube video URL or 11-char ID")


class TranscriptResponse(BaseModel):
    video_id: str
    title: str
    chunk_count: int
    message: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    model: Optional[str] = Field(default=None, description="Ollama model name")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_k: Optional[int] = Field(default=None, ge=1, le=10)


class AskResponse(BaseModel):
    answer: str
    model: str
    video_id: Optional[str]
    sources: list[str]
    evaluation: Optional[dict] = None


# ── Endpoints ────────────────────────────────────────────────────────────────
@router.get("/health")
async def health():
    """Health-check endpoint."""
    return {
        "status": "ok",
        "pipeline_ready": pipeline.is_ready,
        "current_video": pipeline.current_video_id,
    }


@router.get("/models")
async def list_models():
    """Return the configured models and their availability in Ollama."""
    models = await ModelService.list_available()
    return {"models": models}


@router.post("/transcript", response_model=TranscriptResponse)
async def load_transcript(body: TranscriptRequest):
    """Fetch a YouTube transcript, chunk it, and index it in the vector store."""
    input_str = body.video_url_or_id.strip()
    
    # Simple ID extraction (more robust parsing happens on frontend, but backend should handle too)
    video_id = input_str
    if "youtube.com" in input_str or "youtu.be" in input_str:
        if "v=" in input_str:
            video_id = input_str.split("v=")[1].split("&")[0]
        elif "youtu.be/" in input_str:
            video_id = input_str.split("youtu.be/")[1].split("?")[0]

    try:
        data = await TranscriptService.fetch(video_id)
        transcript = data["transcript"]
        title = data["title"]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    chunk_count = pipeline.ingest(transcript, video_id)
    return TranscriptResponse(
        video_id=video_id,
        title=title,
        chunk_count=chunk_count,
        message=f"Successfully indexed '{title}' ({chunk_count} chunks).",
    )


@router.post("/ask", response_model=AskResponse)
async def ask_question(body: AskRequest):
    """Run the RAG pipeline: retrieve context → generate answer."""
    if not pipeline.is_ready:
        raise HTTPException(
            status_code=400,
            detail="No transcript loaded. Load a video first via /api/transcript.",
        )

    model = body.model or settings.DEFAULT_MODEL
    if model not in settings.AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' is not available. Choose from: {settings.AVAILABLE_MODELS}",
        )

    # Hyperparameters
    temp = body.temperature if body.temperature is not None else settings.DEFAULT_TEMPERATURE
    topk = body.top_k if body.top_k is not None else settings.DEFAULT_TOP_K

    try:
        result = pipeline.ask(
            body.question, 
            model_name=model,
            temperature=temp,
            top_k=topk
        )
    except Exception as exc:
        logger.exception("Error during RAG ask")
        raise HTTPException(status_code=500, detail=str(exc))

    return AskResponse(**result)
