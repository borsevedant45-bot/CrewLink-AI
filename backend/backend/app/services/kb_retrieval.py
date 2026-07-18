"""Doc #4 §2 — Chroma retrieval for the Ask CrewLink grounding boundary.

Provides ``retrieve_chunks()`` which queries the ``crewlink_kb`` Chroma
collection and returns chunks with similarity scores.  The caller is
responsible for applying the ``MIN_GROUNDING_SIMILARITY`` threshold
(0.75, per ADDENDUM G8).

This is the ONLY module in the codebase that imports chromadb directly —
the retrieval call is syntactically unreachable from any non-FACILITY
branch (Doc #4 §2 code-level guarantee).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import chromadb

from backend.app.core.config import settings

logger = logging.getLogger("crewlink.kb_retrieval")


@dataclass
class RetrievedChunk:
    """A single chunk returned from Chroma with its similarity score."""

    chunk_id: str
    text: str
    metadata: dict[str, Any]
    similarity: float


async def retrieve_chunks(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Query Chroma KB and return chunks as dicts (for serialization).

    Args:
        query: The search query (in English, per Doc #8 §3.3).
        top_k: Maximum chunks to retrieve (default 5, matches Doc #4 §2).

    Returns:
        List of dicts with keys: chunk_id, text, metadata, similarity.
        Empty list if Chroma is unreachable or returns nothing.

    Logs:
        INFO: query text, chunk count, top similarity score.
        WARNING: empty or below-threshold results.
    """
    try:
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        collection = client.get_collection("crewlink_kb")
    except Exception:
        logger.warning("Chroma retrieval failed — KB store unreachable", exc_info=True)
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        logger.warning("Chroma query failed", exc_info=True)
        return []

    if not results["ids"] or not results["ids"][0]:
        logger.info("KB retrieval: query=%s  chunks=%d  top_sim=N/A (empty)", query, 0)
        return []

    chunks: list[dict[str, Any]] = []
    for i in range(len(results["ids"][0])):
        distance = (results["distances"] or [[0.0]])[0][i]
        similarity = 1.0 - distance
        chunks.append({
            "chunk_id": results["ids"][0][i],
            "text": (results["documents"] or [[""]])[0][i],
            "metadata": (results["metadatas"] or [[{}]])[0][i],
            "similarity": similarity,
        })

    top_sim = chunks[0]["similarity"] if chunks else 0.0
    logger.info(
        "KB retrieval: query=%s  chunks=%d  top_sim=%.4f",
        query, len(chunks), top_sim,
    )

    if not chunks or top_sim < settings.min_grounding_similarity:
        logger.warning(
            "KB retrieval below threshold: query=%s  chunks=%d  top_sim=%.4f",
            query, len(chunks), top_sim,
        )

    return chunks
