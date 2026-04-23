import os
import logging
from flask import request, jsonify
from infosci_spark_client import LLMClient

logger = logging.getLogger(__name__)


def _extract_query_terms(client: LLMClient, user_query: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You extract search terms for a college search engine. "
                "Given a student's natural language query, return 2-5 key search terms. "
                "If the student mentions a specific school by name (e.g. 'Cornell', 'MIT', 'Harvard'), "
                "always include that exact school name as one term, then add 2-3 specific defining traits "
                "of that school, things like its academic strengths, affiliation, size, or setting "
                "(e.g. for Cornell: 'Cornell ivy league research engineering'; "
                "for MIT: 'MIT engineering science'; for NYU: 'NYU urban arts city'). "
                "Pick traits that are genuinely specific to that school, not generic filler. "
                "For queries without a school name, return descriptive trait words only. "
                "Return ONLY the search terms separated by spaces. No punctuation, no explanation."
            ),
        },
        {"role": "user", "content": user_query},
    ]
    response = client.chat(messages)
    terms = (response.get("content") or "").strip()
    logger.info(f"Extracted query: {terms!r} from {user_query!r}")
    return terms or user_query


def _generate_summary(client: LLMClient, user_query: str, schools: list) -> str:
    if not schools:
        return ""
    school_context = "\n".join(
        f"- {s['title']}: {s['descr'][:200]}"
        for s in schools[:5]
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful college counselor. Given a student's query and the top "
                "matching schools from a search engine, write 1-2 sentences explaining why "
                "these schools are a good match. Be specific and encouraging."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Student query: \"{user_query}\"\n\n"
                f"Top matching schools:\n{school_context}"
            ),
        },
    ]
    response = client.chat(messages)
    return (response.get("content") or "").strip()


def register_llm_search_route(app, school_search):
    @app.route("/api/llm-search", methods=["POST"])
    def llm_search():
        data = request.get_json() or {}
        user_query = (data.get("query") or "").strip()

        if not user_query:
            return jsonify({"error": "query is required"}), 400

        api_key = os.getenv("SPARK_API_KEY")
        client = LLMClient(api_key=api_key) if api_key else None

        extracted_query = user_query
        llm_error = None
        if client:
            try:
                extracted_query = _extract_query_terms(client, user_query)
            except Exception as e:
                llm_error = f"rewrite_failed: {e}"
                logger.warning(llm_error)

        schools = school_search(
            extracted_query,
            include_national=data.get("includeNational", True),
            include_liberal_arts=data.get("includeLiberalArts", True),
            user_sat=data.get("sat"),
            user_act=data.get("act"),
            user_gpa=data.get("gpa"),
            user_gpa_out_of=data.get("gpaOutOf"),
        )

        llm_summary = ""
        if client:
            try:
                llm_summary = _generate_summary(client, user_query, schools)
            except Exception as e:
                err = f"answer_failed: {e}"
                llm_error = (llm_error + "; " if llm_error else "") + err
                logger.warning(err)

        payload = {
            "schools": schools,
            "extractedQuery": extracted_query,
            "llmSummary": llm_summary,
        }
        if llm_error:
            payload["llmError"] = llm_error

        return jsonify(payload)
