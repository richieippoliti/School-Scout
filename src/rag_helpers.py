"""
Helpers for LLM-backed query rewriting and RAG answer generation.

These helpers are intentionally separate from Flask route handlers so the
logic is easier to test and debug.
"""

from __future__ import annotations

import json
from typing import Any


def build_rewrite_prompt(user_query: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You rewrite student college-search queries to improve retrieval. "
                "Do NOT answer the question. Do NOT add facts. "
                "Preserve the user's intent, but add useful synonyms and make the query more retrieval-friendly. "
                "Return ONLY the rewritten query text."
            ),
        },
        {"role": "user", "content": user_query.strip()},
    ]


def rewrite_query_with_llm(client, user_query: str) -> str | None:
    user_query = (user_query or "").strip()
    if not user_query:
        return None
    resp = client.chat(build_rewrite_prompt(user_query))
    text = (resp.get("content") or "").strip()
    if not text:
        return None
    # Keep it compact; long rewrites can hurt retrieval.
    return text[:500]


def _results_to_context(results: list[dict[str, Any]], max_results: int = 8) -> str:
    rows = []
    for r in results[:max_results]:
        title = (r.get("title") or r.get("name") or "Unknown").strip()
        city = r.get("city") or ""
        state = r.get("state") or ""
        loc = ", ".join([p for p in (city, state) if p])
        score = r.get("score")
        summary = (r.get("descr") or "").strip()
        chunks = r.get("matchingChunks") or []
        chunk_text = "\n".join(f"- {c}" for c in chunks[:2] if isinstance(c, str) and c.strip())
        rows.append(
            "\n".join(
                [
                    f"School: {title}" + (f" ({loc})" if loc else ""),
                    f"RetrievalScore: {score}",
                    f"Summary: {summary[:600]}",
                    ("Evidence:\n" + chunk_text) if chunk_text else "",
                ]
            ).strip()
        )
    return "\n\n---\n\n".join(rows).strip()


def build_rag_prompt(
    *,
    user_query: str,
    retrieved_results: list[dict[str, Any]],
    rewritten_query: str | None,
) -> list[dict[str, str]]:
    context = _results_to_context(retrieved_results)
    rq = (rewritten_query or "").strip()
    rewrite_line = f"Rewritten query (for retrieval): {rq}\n" if rq else ""
    return [
        {
            "role": "system",
            "content": (
                "You are a college recommendation assistant. "
                "You MUST answer using ONLY the retrieved school context provided. "
                "If the context is insufficient, say what is missing and avoid guessing. "
                "Be concise and grounded: cite which schools support each point."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original query: {user_query.strip()}\n"
                + rewrite_line
                + "\nRetrieved school context:\n\n"
                + (context or "No retrieved results.")
                + "\n\nTask: Recommend 3-5 schools from the retrieved context and explain why each fits."
            ),
        },
    ]


def generate_rag_answer(
    client,
    *,
    user_query: str,
    retrieved_results: list[dict[str, Any]],
    rewritten_query: str | None = None,
) -> str | None:
    if not retrieved_results:
        return None
    resp = client.chat(build_rag_prompt(user_query=user_query, retrieved_results=retrieved_results, rewritten_query=rewritten_query))
    text = (resp.get("content") or "").strip()
    return text or None

