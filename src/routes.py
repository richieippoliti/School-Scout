"""
Routes: React app serving and school search API.
"""
import os
import re
import json
import csv
from flask import send_from_directory, request, jsonify
from models import db, School
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

# AI toggle
# USE_LLM = False
USE_LLM = True
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

_national_rank_by_name: dict[str, int] | None = None
_liberal_arts_rank_by_name: dict[str, int] | None = None


def _norm_school_name(name: str) -> str:
    """
    Best-effort normalization so rankings files match DB school names.
    """
    s = (name or "").strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[\.\-–—']", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _ensure_rank_indexes_loaded():
    """
    Lazy-load ranking mappings from:
      - data/data_filtered.csv (national universities, via sortRank)
      - data/liberal_arts_ranking.json (ordered ranking list)
    """
    global _national_rank_by_name, _liberal_arts_rank_by_name
    if _national_rank_by_name is not None and _liberal_arts_rank_by_name is not None:
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # National universities: rank from CSV sortRank
    nat: dict[str, int] = {}
    csv_path = os.path.join(project_root, "data", "data_filtered.csv")
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get("schoolType") or "").strip().lower() != "national-universities":
                    continue
                nm = row.get("displayName") or ""
                try:
                    r = int(float(str(row.get("sortRank", "")).strip()))
                except (TypeError, ValueError):
                    continue
                if r <= 0:
                    continue
                nat[_norm_school_name(nm)] = r
    except FileNotFoundError:
        nat = {}

    # Liberal arts: ordered JSON list; index+1 is rank
    la: dict[str, int] = {}
    la_path = os.path.join(project_root, "data", "liberal_arts_ranking.json")
    try:
        with open(la_path, "r", encoding="utf-8") as f:
            raw = f.read()
        raw = (raw or "").strip()
        if not raw:
            data = []
        else:
            data = json.loads(raw)
        if isinstance(data, list):
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                nm = item.get("name")
                if not nm:
                    continue
                la[_norm_school_name(str(nm))] = i + 1
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        la = {}

    _national_rank_by_name = nat
    _liberal_arts_rank_by_name = la


def _rank_band_from_sat(sat: int) -> tuple[int | None, int | None]:
    """
    Convert SAT into an allowed ranking band:
      - min_rank: don't suggest schools more selective than this (e.g. exclude top 10)
      - max_rank: don't suggest schools less selective than this (e.g. only top 100)
    """
    if sat >= 1500:
        return (1, 100)
    if sat >= 1450:
        return (1, 150)
    if sat >= 1400:
        return (1, 200)
    if sat >= 1300:
        return (10, 350)
    if sat >= 1200:
        return (11, 500)
    if sat >= 1100:
        return (25, 700)
    # very low / unknown prep: avoid the most selective schools
    return (60, None)


def _rank_band_from_act(act: float) -> tuple[int | None, int | None]:
    if act >= 34:
        return (1, 100)
    if act >= 32:
        return (1, 150)
    if act >= 30:
        return (1, 250)
    if act >= 27:
        return (10, 450)
    if act >= 24:
        return (25, 700)
    return (60, None)


def _rank_band_from_gpa_on_4(gpa: float) -> tuple[int | None, int | None]:
    if gpa >= 3.9:
        return (1, 100)
    if gpa >= 3.7:
        return (1, 150)
    if gpa >= 3.5:
        return (1, 250)
    if gpa >= 3.2:
        return (15, 500)
    if gpa >= 3.0:
        return (35, 800)
    return (70, None)


def _combine_rank_bands(*bands: tuple[int | None, int | None]) -> tuple[int | None, int | None]:
    mins = [b[0] for b in bands if b[0] is not None]
    maxs = [b[1] for b in bands if b[1] is not None]
    min_rank = max(mins) if mins else None
    max_rank = min(maxs) if maxs else None
    return (min_rank, max_rank)


def _school_rank(school: School) -> int | None:
    _ensure_rank_indexes_loaded()
    t = (getattr(school, "institution_type", None) or "national_university").strip().lower()
    nm = _norm_school_name(school.name)
    if t == "liberal_arts":
        return (_liberal_arts_rank_by_name or {}).get(nm)
    return (_national_rank_by_name or {}).get(nm)


def _school_passes_rank_band(school: School, min_rank: int | None, max_rank: int | None) -> bool:
    if min_rank is None and max_rank is None:
        return True
    r = _school_rank(school)
    # If we can't rank the school, don't block it (keeps coverage high).
    if r is None:
        return True
    if min_rank is not None and r < min_rank:
        return False
    if max_rank is not None and r > max_rank:
        return False
    return True


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
    
    corpus = []
    for school in _indexed_schools:
        reviews_text = ""
        if school.reviews_json:
            try:
                reviews = json.loads(school.reviews_json)
                reviews_text = " ".join([review.get('text', '') for review in reviews if review.get('text')])
            except (json.JSONDecodeError, TypeError):
                reviews_text = ""
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
    max_components = min(n_samples - 1, n_features - 1, 128)
    if max_components >= 1:
        _svd = TruncatedSVD(n_components=max_components, random_state=42)
        _doc_lsa = _svd.fit_transform(_tfidf_matrix)
    
def _get_top_query_terms(query_vec, top_n: int = 8) -> list:
    feature_names = _vectorizer.get_feature_names_out()
    cx = query_vec.tocsr()
    if cx.nnz == 0:
        return []
    weights = [(feature_names[j], float(cx[0, j])) for j in cx.indices]
    weights.sort(key=lambda x: x[1], reverse=True)
    unigrams = [w for w, _ in weights if ' ' not in w and not w.startswith('NOT_')]
    bigrams  = [w for w, _ in weights if ' '     in w and not w.startswith('NOT_')]
    return (unigrams + bigrams)[:top_n]


_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')

def _extract_matching_chunks(school, query_terms: list, max_chunks: int = 2, max_len: int = 160) -> list:
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


def _parse_bool_param(value, default: bool) -> bool:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    s = str(value).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return default


def _optional_int_param(value):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _optional_float_param(value):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    try:
        f = float(str(value).strip())
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _school_passes_dataset_filter(
    school: School, include_national: bool, include_liberal: bool
) -> bool:
    t = (getattr(school, "institution_type", None) or "national_university").strip().lower()
    if t == "liberal_arts":
        return include_liberal
    if t == "national_university":
        return include_national
    return include_national or include_liberal


def _school_passes_stats_filter(
    school: School,
    user_sat: int | None,
    user_act: float | None,
    user_gpa_on_4: float | None,
) -> bool:
    """
    We don't reliably have SAT/ACT/GPA for many schools, so instead:
      - convert user SAT/ACT/GPA into a *ranking band* (min/max rank)
      - filter schools by rank (US News-ish) rather than by published test/GPA stats

    Rank sources:
      - national universities: data/data_filtered.csv (sortRank)
      - liberal arts colleges: data/liberal_arts_ranking.json order
    """
    bands: list[tuple[int | None, int | None]] = []
    if user_sat is not None:
        bands.append(_rank_band_from_sat(int(user_sat)))
    if user_act is not None:
        bands.append(_rank_band_from_act(float(user_act)))
    if user_gpa_on_4 is not None:
        bands.append(_rank_band_from_gpa_on_4(float(user_gpa_on_4)))

    min_rank, max_rank = _combine_rank_bands(*bands) if bands else (None, None)
    return _school_passes_rank_band(school, min_rank, max_rank)


def school_search(
    query,
    top_k=20,
    threshold=0.05,
    metric="tfidf",
    *,
    include_national: bool = True,
    include_liberal_arts: bool = True,
    user_sat: int | None = None,
    user_act: float | None = None,
    user_gpa: float | None = None,
    user_gpa_out_of: float | None = None,
):
    global _vectorizer, _tfidf_matrix, _indexed_schools, _svd, _doc_lsa
    if not query or not query.strip():
        return []
    if _vectorizer is None:
        _build_index()
    if _vectorizer is None:
        return []

    if not include_national and not include_liberal_arts:
        return []

    m = (metric or "tfidf").strip().lower()
    if m not in ("tfidf", "svd"):
        m = "tfidf"

    user_gpa_on_4 = None
    if (
        user_gpa is not None
        and user_gpa_out_of is not None
        and user_gpa_out_of > 0
    ):
        user_gpa_on_4 = (user_gpa / user_gpa_out_of) * 4.0

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

    query_terms = _get_top_query_terms(query_vec)

    def _json_float(value):
        """Ensure JSON-serializable native float for coordinates (avoids numpy / Decimal quirks)."""
        if value is None:
            return None
        return float(value)

    def _school_payload(score: float, school: School) -> dict:
        reviews = []
        if school.reviews_json:
            try:
                raw_reviews = json.loads(school.reviews_json)
                if isinstance(raw_reviews, list):
                    reviews = raw_reviews
            except (json.JSONDecodeError, TypeError):
                reviews = []
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
            "institutionType": getattr(school, "institution_type", None) or "national_university",
            "nicheUrl": school.niche_url,
            "reviews": reviews,
            "matchingChunks": _extract_matching_chunks(school, query_terms),
            "queryTerms": query_terms,
        }

    out = []
    for score, school in ranked:
        if not _school_passes_dataset_filter(school, include_national, include_liberal_arts):
            continue
        if not _school_passes_stats_filter(school, user_sat, user_act, user_gpa_on_4):
            continue
        out.append(_school_payload(score, school))
        if len(out) >= top_k:
            break
    return out
    
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
        include_national = _parse_bool_param(
            request.args.get("include_national"), True
        )
        include_liberal_arts = _parse_bool_param(
            request.args.get("include_liberal_arts"), True
        )
        user_sat = _optional_int_param(request.args.get("sat"))
        user_act = _optional_float_param(request.args.get("act"))
        user_gpa = _optional_float_param(request.args.get("gpa"))
        user_gpa_out_of = _optional_float_param(request.args.get("gpa_out_of"))
        return jsonify(
            school_search(
                text,
                metric=metric,
                include_national=include_national,
                include_liberal_arts=include_liberal_arts,
                user_sat=user_sat,
                user_act=user_act,
                user_gpa=user_gpa,
                user_gpa_out_of=user_gpa_out_of,
            )
        )

    if USE_LLM:
        from llm_routes import register_llm_search_route
        register_llm_search_route(app, school_search)
