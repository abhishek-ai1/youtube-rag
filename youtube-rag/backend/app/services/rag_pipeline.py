"""Core RAG pipeline: split → embed → store → retrieve → generate."""

import logging
from typing import List, Dict, Any, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)

# ── Prompt template ──────────────────────────────────────────────────────────
QA_PROMPT = PromptTemplate(
    template="""
You answer questions using only the context below.
If the answer is not in the context, say "I don't know."

Context:
{context}

Question: {question}

Answer:
""",
    input_variables=["context", "question"],
)


class RAGPipeline:
    """
    Production-grade Retrieval-Augmented Generation pipeline.
    
    Includes lazy loading, hyperparameter tuning, and basic performance evaluation.
    """

    def __init__(self) -> None:
        self._vectorstore: Optional[InMemoryVectorStore] = None
        self._embeddings = None  # Lazy load
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        self._video_id: Optional[str] = None

    def _get_embeddings(self) -> OllamaEmbeddings:
        """Lazy load embeddings provider."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=settings.EMBEDDING_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )
        return self._embeddings

    # ── Public API ───────────────────────────────────────────────────────────

    def ingest(self, transcript: str, video_id: str) -> int:
        """Split transcript into chunks and index them."""
        chunks: List[Document] = self._splitter.create_documents(
            [transcript],
            metadatas=[{"video_id": video_id}],
        )
        self._vectorstore = InMemoryVectorStore.from_documents(
            chunks,
            self._get_embeddings(),
        )
        self._video_id = video_id
        logger.info("[OBSERVABILITY] Ingested %d chunks for %s", len(chunks), video_id)
        return len(chunks)

    def ask(
        self, 
        question: str, 
        model_name: str = settings.DEFAULT_MODEL,
        temperature: float = settings.DEFAULT_TEMPERATURE,
        top_k: int = settings.DEFAULT_TOP_K
    ) -> Dict[str, Any]:
        """
        Retrieve context and generate an answer with confidence scoring.
        """
        # Guardrail: Basic sanitization
        if not question or len(question.strip()) < 3:
            return {"answer": "I'm sorry, that query is too short for me to process.", "confidence": 0.0}
        
        if len(question) > 1000:
            return {"answer": "Queston is too long for the current context window.", "confidence": 0.0}

        if self._vectorstore is None:
            raise RuntimeError("No transcript loaded. Please load a video first.")

        # Retrieval with Similarity Scoring (Evaluation)
        docs_with_scores = self._vectorstore.similarity_search_with_score(question, k=top_k)
        
        if not docs_with_scores:
            return {"answer": "I don't find any relevant info in this video for that.", "confidence": 0.0}

        # Calculate average confidence score (1 - normalized distance)
        # InMemoryVectorStore usually returns Cosine Distance or L2
        avg_dist = sum(score for _, score in docs_with_scores) / len(docs_with_scores)
        confidence = max(0.0, min(1.0, 1.0 - (avg_dist / 2.0)))  # Basic heuristic

        context_text = "\n\n".join(doc.page_content for doc, _ in docs_with_scores)

        # Lazy load/init LLM with parameters
        llm = Ollama(
            model=model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
        )
        
        final_prompt = QA_PROMPT.format(context=context_text, question=question)
        answer = llm.invoke(final_prompt)

        logger.info(
            "[EVALUATION] GenAnswer | Model: %s | Temp: %.1f | K: %d | Confidence: %.2f",
            model_name, temperature, top_k, confidence
        )

        return {
            "answer": answer.strip(),
            "model": model_name,
            "video_id": self._video_id,
            "sources": [doc.page_content[:250] for doc, _ in docs_with_scores],
            "evaluation": {
                "confidence_score": round(float(confidence), 3),
                "top_k": top_k,
                "retrieval_dist": round(float(avg_dist), 4)
            }
        }

    @property
    def is_ready(self) -> bool:
        return self._vectorstore is not None

    @property
    def current_video_id(self) -> Optional[str]:
        return self._video_id
