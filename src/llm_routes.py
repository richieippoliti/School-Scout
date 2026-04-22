"""
LLM-backed routes.

Design goals:
- Retrieval remains the source of truth (RAG, not a generic chatbot)
- The route always returns IR results; LLM answer is an enhancement
- Fail gracefully when the LLM is unavailable
"""
import os
import logging
from flask import request, jsonify
from infosci_spark_client import LLMClient

logger = logging.getLogger(__name__)

from semantic_filters import extract_semantic_filters
from rag_helpers import rewrite_query_with_llm, generate_rag_answer

def _optional_bool(d: dict, key: str, default: bool) -> bool:
    v = d.get(key)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return default


def _optional_float(d: dict, key: str):
    v = d.get(key)
    if v is None or v == "":
        return None
    try:
        f = float(str(v).strip())
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _optional_int(d: dict, key: str):
    v = d.get(key)
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def register_llm_routes(app, school_search):
    """
    Register LLM-backed routes.

    - POST /api/schools/rag
      Input: { query, metric?, includeNational?, includeLiberalArts?, sat?, act?, gpa?, gpaOutOf? }
      Output: { original_query, rewritten_query, results, llm_answer, applied_filters, metadata? }
    """

    @app.route("/api/schools/rag", methods=["POST"])
    def rag_search():
        data = request.get_json() or {}
        original_query = (data.get("query") or "").strip()
        if not original_query:
            return jsonify({"error": "query is required"}), 400

        metric = (data.get("metric") or "tfidf").strip()
        include_national = _optional_bool(data, "includeNational", True)
        include_liberal = _optional_bool(data, "includeLiberalArts", True)
        user_sat = _optional_int(data, "sat")
        user_act = _optional_float(data, "act")
        user_gpa = _optional_float(data, "gpa")
        user_gpa_out_of = _optional_float(data, "gpaOutOf")

        semantic_filters = extract_semantic_filters(original_query)

        api_key = os.getenv("SPARK_API_KEY")
        client = LLMClient(api_key=api_key) if api_key else None

        rewritten_query = None
        retrieval_query = original_query
        llm_error = None

        # Step 1-3: optional rewrite (LLM), then retrieval using the existing pipeline.
        if client is not None:
            try:
                rewritten_query = rewrite_query_with_llm(client, original_query)
                if rewritten_query:
                    retrieval_query = rewritten_query
            except Exception as e:
                llm_error = f"rewrite_failed: {e}"
                logger.warning(llm_error)

        results = school_search(
            retrieval_query,
            metric=metric,
            include_national=include_national,
            include_liberal_arts=include_liberal,
            user_sat=user_sat,
            user_act=user_act,
            user_gpa=user_gpa,
            user_gpa_out_of=user_gpa_out_of,
            semantic_filters=semantic_filters,
        )

        llm_answer = None
        if client is not None:
            try:
                llm_answer = generate_rag_answer(
                    client,
                    user_query=original_query,
                    retrieved_results=results,
                    rewritten_query=rewritten_query,
                )
            except Exception as e:
                llm_error = (llm_error + "; " if llm_error else "") + f"answer_failed: {e}"
                logger.warning(llm_error)

        payload = {
            "original_query": original_query,
            "rewritten_query": rewritten_query,
            "results": results,
            "llm_answer": llm_answer,
            "applied_filters": {
                "include_national": include_national,
                "include_liberal_arts": include_liberal,
                "sat": user_sat,
                "act": user_act,
                "gpa": user_gpa,
                "gpa_out_of": user_gpa_out_of,
                "semantic": semantic_filters.as_json(),
            },
        }
        if llm_error:
            payload["metadata"] = {"llm_error": llm_error}

        return jsonify(payload)
