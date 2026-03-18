"""
Routes: React app serving and school search API.

To enable AI chat, set USE_LLM = True below. See llm_routes.py for AI code.
"""
import os
from flask import send_from_directory, request, jsonify
from models import db, School

# ── AI toggle ────────────────────────────────────────────────────────────────
USE_LLM = False
# USE_LLM = True
# ─────────────────────────────────────────────────────────────────────────────


def school_search(query):
    if not query or not query.strip():
        return []
    results = School.query.filter(
        School.summary.ilike(f'%{query}%')
    ).all()
    return [
        {
            'title': school.name,
            'descr': school.summary,
            'imdb_rating': school.avg_rating
        }
        for school in results
    ]


def register_routes(app):
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')

    @app.route("/api/config")
    def config():
        return jsonify({"use_llm": USE_LLM})

    @app.route("/api/episodes")
    def episodes_search():
        text = request.args.get("title", "")
        return jsonify(school_search(text))

    if USE_LLM:
        from llm_routes import register_chat_route
        register_chat_route(app, school_search)
