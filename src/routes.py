"""
Routes: React app serving and school search API.
"""
import os
import re
import json
from flask import send_from_directory, request, jsonify
from models import db, School
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
    if _nlp is None:
        return text
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
    
def _get_top_query_terms(query_vec, top_n: int = 8) -> list:
    """Return the highest-weighted vocabulary terms from a query TF-IDF vector."""
    feature_names = _vectorizer.get_feature_names_out()
    cx = query_vec.tocsr()
    if cx.nnz == 0:
        return []
    weights = [(feature_names[j], float(cx[0, j])) for j in cx.indices]
    weights.sort(key=lambda x: x[1], reverse=True)
    # Prefer unigrams (readable words); also grab top bigrams for specificity
    unigrams = [w for w, _ in weights if ' ' not in w and not w.startswith('NOT_')]
    bigrams  = [w for w, _ in weights if ' '     in w and not w.startswith('NOT_')]
    return (unigrams + bigrams)[:top_n]


_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')

def _extract_matching_chunks(school, query_terms: list, max_chunks: int = 2, max_len: int = 160) -> list:
    """
    Find up to max_chunks sentences from the school's reviews / summary that
    contain the most query-relevant terms. Used to show the user *why* a
    school matched their query.
    """
    if not query_terms:
        return []

    sentences = []

    if school.reviews_json:
        try:
            reviews = json.loads(school.reviews_json)
            for review in reviews:
                text = review.get('text', '')
                if text:
                    for s in _SENTENCE_RE.split(text.strip()):
                        s = s.strip()
                        if len(s) > 25:
                            sentences.append(s)
        except (json.JSONDecodeError, TypeError):
            pass

    if school.summary:
        for s in _SENTENCE_RE.split(school.summary.strip()):
            s = s.strip()
            if len(s) > 25:
                sentences.append(s)

    terms_lower = [t.lower() for t in query_terms]
    seen: set = set()
    scored = []

    for sent in sentences:
        sent_lower = sent.lower()
        score = sum(1 for term in terms_lower if term in sent_lower)
        if score == 0:
            continue
        key = sent_lower[:60]
        if key in seen:
            continue
        seen.add(key)
        display = sent if len(sent) <= max_len else sent[:max_len].rsplit(' ', 1)[0] + '…'
        scored.append((score, display))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:max_chunks]]


def school_search(query, top_k=20, threshold=0.05, metric="tfidf"):
    global _vectorizer, _tfidf_matrix, _indexed_schools, _svd, _doc_lsa
    if not query or not query.strip():
        return []
    if _vectorizer is None:
        _build_index()
    if _vectorizer is None:
        return []

    m = (metric or "tfidf").strip().lower()
    if m not in ("tfidf", "svd"):
        m = "tfidf"

    query_vec = _vectorizer.transform([query.strip()])
    if m == "svd" and _svd is not None and _doc_lsa is not None:
        q_lsa = _svd.transform(query_vec)
        scores = cosine_similarity(q_lsa, _doc_lsa).flatten()
    else:
        scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()

    ranked = sorted(
        ((score, school) for score, school in zip(scores, _indexed_schools)
         if score >= threshold), # Results below threshold discarded
        key=lambda x: x[0],
        reverse=True,
    )
    print([(round(float(s), 4), sc.name) for s, sc in ranked[:5]])

    # Always use TF-IDF terms for chunk extraction (human-readable keywords)
    query_terms = _get_top_query_terms(query_vec)

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
            "matchingChunks": _extract_matching_chunks(school, query_terms),
            "queryTerms": query_terms,
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
        return jsonify(school_search(text, metric=metric))

    if USE_LLM:
        from llm_routes import register_chat_route
        register_chat_route(app, school_search)