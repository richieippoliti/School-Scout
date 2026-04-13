"""
Routes: React app serving and school search API.
"""
import os
import json
import numpy as np
from flask import send_from_directory, request, jsonify
from models import db, School
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

# AI toggle
USE_LLM = False
# USE_LLM = True
_vectorizer: TfidfVectorizer | None = None
_tfidf_matrix = None
_svd: TruncatedSVD | None = None
_doc_lsa = None  # document vectors in reduced space (LSA)
_indexed_schools: list = []

def _load_spacy():
    """Lazy-load spaCy small English model. Returns None if unavailable."""
    try:
        import spacy
        # disable everything except the dependency parser — we don't need
        # NER or the tagger, and this makes processing ~3x faster.
        return spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    except (ImportError, OSError):
        return None
 
_nlp = _load_spacy()


def _apply_negation_marking(text: str) -> str:
    """
    Return text with negated tokens prefixed by NOT_.
 
    Uses spaCy's dependency tree when available:
      - finds every token whose dependency label is "neg"
      - prefixes that token's syntactic HEAD with NOT_
      - this correctly handles "not only safe" (head=safe) vs the window
        approach which would mark "only" and "safe" both
    """
    return _apply_negation_marking_spacy(text)
 
 
def _apply_negation_marking_spacy(text: str) -> str:
    """
    spaCy dependency-tree negation marking.
 
    For every negation token (dep_ == "neg"), mark its head word with NOT_.
    The negation token itself is dropped so it doesn't pollute the vocabulary.
 
    Example parse of "not safe campus":
        not   -> dep_="neg",  head="safe"
        safe  -> dep_="amod", head="campus"   <- gets marked NOT_safe
        campus-> dep_="ROOT"
    """
    doc = _nlp(text)
 
    # Collect indices of tokens whose HEAD should be marked
    negated_heads = {token.head.i for token in doc if token.dep_ == "neg"}
 
    tokens = []
    for token in doc:
        if token.dep_ == "neg":
            continue
        if token.i in negated_heads:
            tokens.append(f"NOT_{token.lemma_.lower()}")
        else:
            tokens.append(token.text.lower())
 
    return " ".join(tokens)

# The Gaussian formula:
#   score = exp(-0.5 * ((school_value - target) / sigma) ** 2)

_FIELD_DEFAULTS: dict[str, tuple[str, float]] = {
    "satAvg": ("sat_avg", 100.0),
    "actAvg": ("act_avg", 3.0),
    "hsGpaAvg":("hs_gpa_avg",0.3),
    "acceptanceRate":("acceptance_rate", 10.0),
    "satEla50": ("sat_ela_50", 100.0),
    "satEla75": ("sat_ela_75", 100.0),
    "satMath50":("sat_math_50", 100.0),
    "satMath75":("sat_math_75", 100.0),
    "actComp50":("act_comp_50",3.0),
    "actComp75":("act_comp_75",3.0),
}

@dataclass
class NumericFilter:
    """One numeric preference expressed by the caller."""
    model_attr: str   # attribute name on the School ORM object
    target: float     # value the user is aiming for
    sigma: float      # tolerance — higher = looser
 
 
def _parse_numeric_filters(params: dict) -> list[NumericFilter]:
    """
    Build a list of NumericFilter objects from raw request query params.
 
    Accepted formats:
        ?satAvg=1200                    target=1200, default sigma
        ?satAvg=1200&satAvg_sigma=50    target=1200, custom sigma=50
        ?acceptanceRate=40              target=40%, default sigma=15
    Multiple filters can be combined in one request.
    """
    filters = []
    for api_key, (model_attr, default_sigma) in _FIELD_DEFAULTS.items():
        raw = params.get(api_key)
        if raw is None:
            continue
        try:
            target = float(raw)
        except (ValueError, TypeError):
            continue
        try:
            sigma = float(params.get(f"{api_key}_sigma", default_sigma))
        except (ValueError, TypeError):
            sigma = default_sigma
        filters.append(NumericFilter(model_attr=model_attr, target=target, sigma=sigma))
    return filters
 
 
def _gaussian_score(value, target: float, sigma: float) -> float:
    """
    Return a [0, 1] closeness score.
    Missing values (None / NaN) return 0.5 — neutral, not penalised.
    Schools with incomplete data shouldn't be buried just for a data gap.
    """
    if value is None:
        return 0.5
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.5
    if np.isnan(v):
        return 0.5
    return float(np.exp(-0.5 * ((v - target) / sigma) ** 2))
 
 
def _numeric_match_score(school: School, filters: list[NumericFilter]) -> float:
    """
    Mean Gaussian score across all active filters for one school.
    Returns 1.0 (no effect on ranking) when no filters are supplied.
    """
    if not filters:
        return 1.0
    return float(np.mean([
        _gaussian_score(getattr(school, f.model_attr, None), f.target, f.sigma)
        for f in filters
    ]))

def _build_index():
    global _vectorizer, _tfidf_matrix, _indexed_schools, _svd, _doc_lsa

    _indexed_schools = School.query.all()
    if not _indexed_schools:
        _vectorizer = None
        _tfidf_matrix = None
        _svd = None
        _doc_lsa = None
        return
    
    # Build corpus from all reviews for each school, not just the summary
    corpus = []
    for school in _indexed_schools:
        reviews_text = ""
        if school.reviews_json:
            try:
                reviews = json.loads(school.reviews_json)
                reviews_text = " ".join([review.get('text', '') for review in reviews if review.get('text')])
            except (json.JSONDecodeError, TypeError):
                reviews_text = ""
        
        # Combine reviews with summary for better coverage
        combined_text = (reviews_text + " " + (school.summary or "")).strip()
        corpus.append(_apply_negation_marking(combined_text))
    
    _vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        norm = 'l2',
    )
    _tfidf_matrix = _vectorizer.fit_transform(corpus)

    _svd = None
    _doc_lsa = None
    n_samples, n_features = _tfidf_matrix.shape
    # LSA / truncated SVD on TF-IDF (same vocabulary; query projected into topic space)
    max_components = min(n_samples - 1, n_features - 1, 128)
    if max_components >= 1:
        _svd = TruncatedSVD(n_components=max_components, random_state=42)
        _doc_lsa = _svd.fit_transform(_tfidf_matrix)
    
def school_search(query, top_k=20, threshold=0.05, metric="tfidf",
                  numeric_filters: list[NumericFilter] | None = None,
                  numeric_weight: float = 0.25):
    
    global _vectorizer, _tfidf_matrix, _indexed_schools, _svd, _doc_lsa
    if not query or not query.strip():
        return []
    
    if _vectorizer is None:
        _build_index()
    if _vectorizer is None:
        return []
    
    numeric_filters = numeric_filters or []

    m = (metric or "tfidf").strip().lower()
    if m not in ("tfidf", "svd"):
        m = "tfidf"
        
    processed_query = _apply_negation_marking(query.strip())
    query_vec = _vectorizer.transform([processed_query])

    if m == "svd" and _svd is not None and _doc_lsa is not None:
        q_lsa = _svd.transform(query_vec)
        scores = cosine_similarity(q_lsa, _doc_lsa).flatten()
    else:
        scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()
        
    nw = numeric_weight if numeric_filters else 0.0
    rw = 1.0 - nw
    

    # Blend retrieval and numeric signals
    final_scores = np.array([
        rw * float(scores[i])
        + nw * _numeric_match_score(_indexed_schools[i], numeric_filters)
        for i in range(len(_indexed_schools))
    ])

    ranked = sorted(
        (
            (float(final_scores[i]), _indexed_schools[i])
            for i in range(len(_indexed_schools))
        ),
        key=lambda x: x[0],
        reverse=True,
    )
    print(ranked[:5])
    print([(round(fs, 4), sc.name) for fs, sc in ranked[:5]])

    def _json_float(value):
        """Ensure JSON-serializable native float for coordinates (avoids numpy / Decimal quirks)."""
        if value is None:
            return None
        return float(value)

    def _school_payload(score: float, school: School) -> dict:
        return {
            "id": school.id,
            "title": school.name,
            "name": school.name,
            "descr": school.summary,
            "score": round(float(score), 4),
            "latitude": _json_float(school.latitude),
            "longitude": _json_float(school.longitude),
            "acceptanceRate": _json_float(school.acceptance_rate),
            "tuition": school.tuition,
            "enrollment": school.enrollment,
        }

    return [_school_payload(score, school) for score, school in ranked[:top_k]]
    
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
        metric = request.args.get("metric", "tfidf")
        try:
            nw = float(request.args.get("numeric_weight", 0.25))
            nw = max(0.0, min(1.0, nw))
        except (ValueError, TypeError):
            nw = 0.25
 
        numeric_filters = _parse_numeric_filters(request.args)
        
        return jsonify(school_search(
            text,
            metric=metric,
            numeric_filters=numeric_filters,
            numeric_weight=nw,
        ))

    if USE_LLM:
        from llm_routes import register_chat_route
        register_chat_route(app, school_search)