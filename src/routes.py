"""
Routes: React app serving and school search API.
"""
import os
from flask import send_from_directory, request, jsonify
from models import db, School
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# AI toggle
USE_LLM = False
# USE_LLM = True
_vectorizer: TfidfVectorizer | None = None
_tfidf_matrix = None
_indexed_schools: list = []

def _build_index():
    global _vectorizer, _tfidf_matrix, _indexed_schools

    _indexed_schools = School.query.all()
    if not _indexed_schools:
        _vectorizer = None
        _tfidf_matrix = None
        return
    
    corpus = [school.summary or "" for school in _indexed_schools]
    _vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        norm = 'l2',
    )
    _tfidf_matrix = _vectorizer.fit_transform(corpus)
    
def school_search(query, top_k=20, threshold=0.05):
    global _vectorizer, _tfidf_matrix, _indexed_schools
    if not query or not query.strip():
        return []
    if _vectorizer is None:
        _build_index()
    if _vectorizer is None:
        return []

    query_vec = _vectorizer.transform([query.strip()])
    scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    ranked = sorted(
        ((score, school) for score, school in zip(scores, _indexed_schools)
         if score >= threshold), # Results below threshold discarded
        key=lambda x: x[0],
        reverse=True,
    )
    print([(round(float(s), 4), sc.name) for s, sc in ranked[:5]])
    return [
        {
            "title": school.name,
            "descr": school.summary,
            "score": round(float(score), 4),
        }
        for score, school in ranked[:top_k]
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

    @app.route("/api/schools")
    def schools_search():
        text = request.args.get("query", "")
        return jsonify(school_search(text))

    if USE_LLM:
        from llm_routes import register_chat_route
        register_chat_route(app, school_search)