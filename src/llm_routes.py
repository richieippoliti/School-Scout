"""
LLM chat route — only loaded when USE_LLM = True in routes.py.
Adds a POST /api/chat endpoint that performs LLM-driven RAG.

Setup:
  1. Add API_KEY=your_key to .env
  2. Set USE_LLM = True in routes.py
"""
import json
import os
import re
import logging
from flask import request, jsonify, Response, stream_with_context
from infosci_spark_client import LLMClient

logger = logging.getLogger(__name__)


def llm_search_decision(client, user_message):
    """Ask the LLM whether to search the DB and which keyword to use."""
    messages = [
        {
            "role": "system",
            "content": (
                "You help match high school students to colleges. You have access to a database of college "
                "summaries. Search is by a single keyword found in the college description (e.g. a vibe, "
                "location, or trait like 'Christian', 'urban', 'research', 'warm', 'sports'). "
                "Reply with exactly: YES followed by one space and ONE keyword to search (e.g. YES warm), "
                "or NO if the question does not need college data."
            ),
        },
        {"role": "user", "content": user_message},
    ]
    response = client.chat(messages)
    content = (response.get("content") or "").strip().upper()
    logger.info(f"LLM search decision: {content}")
    if re.search(r"\bNO\b", content) and not re.search(r"\bYES\b", content):
        return False, None
    yes_match = re.search(r"\bYES\s+(\w+)", content)
    if yes_match:
        return True, yes_match.group(1).lower()
    if re.search(r"\bYES\b", content):
        return True, "university"
    return False, None


def register_chat_route(app, school_search):
    """Register the /api/chat SSE endpoint. Called from routes.py."""

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.get_json() or {}
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        api_key = os.getenv("API_KEY")
        if not api_key:
            return jsonify({"error": "API_KEY not set — add it to your .env file"}), 500

        client = LLMClient(api_key=api_key)
        use_search, search_term = llm_search_decision(client, user_message)

        if use_search:
            schools = school_search(search_term or "university")
            context_text = "\n\n---\n\n".join(
                f"School: {s['title']}\nSummary: {s['descr']}\nAvg Rating: {s['imdb_rating']}"
                for s in schools
            ) or "No matching schools found."
            messages = [
                {"role": "system", "content": "You are a college counselor helping high school students find their best-fit college. Use only the school information provided to make recommendations. Be encouraging and specific about why each school might suit the student."},
                {"role": "user", "content": f"College information:\n\n{context_text}\n\nStudent question: {user_message}"},
            ]
        else:
            messages = [
                {"role": "system", "content": "You are a college counselor helping high school students find their best-fit college."},
                {"role": "user", "content": user_message},
            ]

        def generate():
            if use_search and search_term:
                yield f"data: {json.dumps({'search_term': search_term})}\n\n"
            try:
                for chunk in client.chat(messages, stream=True):
                    if chunk.get("content"):
                        yield f"data: {json.dumps({'content': chunk['content']})}\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': 'Streaming error occurred'})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
