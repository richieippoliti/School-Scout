import json
import os
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import inspect, text, func

load_dotenv()
from flask_cors import CORS
from models import db, School
from routes import register_routes, _build_index

current_directory = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_directory)
SEED_JSON_PATH = os.path.join(project_root, 'data', 'national_university_data.json')
LIBERAL_ARTS_JSON_PATH = os.path.join(project_root, 'data', 'liberal_arts_colleges.json')

# serve React build files
app = Flask(__name__,
    static_folder=os.path.join(project_root, 'frontend', 'dist'),
    static_url_path='')
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

register_routes(app)


def _optional_float(value):
    if value is None:
        return None
    try:
        f = float(value)
        return f if f == f else None  # NaN check
    except (TypeError, ValueError):
        return None


def _optional_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_differs(stored, new) -> bool:
    if new is None:
        return False
    if stored is None:
        return True
    try:
        return abs(float(stored) - float(new)) > 1e-5
    except (TypeError, ValueError):
        return True


def _geo_bundle_from_school_json(school: dict) -> tuple:
    """Parse optional location / stats from a seed JSON object."""
    lat = _optional_float(school.get('latitude'))
    lng = _optional_float(school.get('longitude'))
    if lat is not None and (lat < -90 or lat > 90):
        lat = None
    if lng is not None and (lng < -180 or lng > 180):
        lng = None
    return (
        _optional_str(school.get('city')),
        _optional_str(school.get('state')),
        lat,
        lng,
        _optional_float(school.get('acceptance_rate', school.get('acceptanceRate'))),
        _optional_int(school.get('tuition')),
        _optional_int(school.get('enrollment')),
    )


def _admissions_stats_from_school_json(school: dict) -> tuple:
    """Optional SAT/ACT/GPA mid-fifties etc., when present in seed JSON."""
    return (
        _optional_float(school.get('sat_25')),
        _optional_float(school.get('sat_75')),
        _optional_float(school.get('act_25')),
        _optional_float(school.get('act_75')),
        _optional_float(school.get('gpa_mid')),
    )


def _name_to_geo_map(records: list[dict]) -> dict[str, tuple]:
    out: dict[str, tuple] = {}
    for school in records:
        name = _optional_str(school.get('school_name'))
        if not name:
            continue
        out[name.lower()] = _geo_bundle_from_school_json(school)
    return out


def _append_schools_from_json_records(
    records: list,
    institution_type: str,
    start_id: int,
    geo_fallback_by_name: dict[str, tuple] | None = None,
) -> tuple[int, int]:
    """
    Insert School rows from a list of seed JSON objects.
    Returns (next_id_after_last_used, number_of_rows_inserted).
    """
    next_id = start_id
    inserted = 0
    for school in records:
        if not school.get('ai_summary'):
            continue
        reviews = school.get('reviews', [])
        avg_rating = (
            sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0.0
        )
        city, state, lat, lng, acc, tuition, enrollment = _geo_bundle_from_school_json(school)
        if geo_fallback_by_name and (lat is None or lng is None):
            fallback = geo_fallback_by_name.get(str(school.get('school_name', '')).strip().lower())
            if fallback:
                f_city, f_state, f_lat, f_lng, f_acc, f_tuition, f_enrollment = fallback
                city = city or f_city
                state = state or f_state
                lat = lat if lat is not None else f_lat
                lng = lng if lng is not None else f_lng
                acc = acc if acc is not None else f_acc
                tuition = tuition if tuition is not None else f_tuition
                enrollment = enrollment if enrollment is not None else f_enrollment
        sat_25, sat_75, act_25, act_75, gpa_mid = _admissions_stats_from_school_json(school)

        db.session.add(
            School(
                id=next_id,
                name=school['school_name'],
                summary=school['ai_summary'],
                reviews_json=json.dumps(reviews),
                avg_rating=round(avg_rating, 2),
                niche_url=_optional_str(school.get('school_url')),
                institution_type=institution_type,
                city=city,
                state=state,
                latitude=lat,
                longitude=lng,
                acceptance_rate=acc,
                tuition=tuition,
                enrollment=enrollment,
                sat_25=sat_25,
                sat_75=sat_75,
                act_25=act_25,
                act_75=act_75,
                gpa_mid=gpa_mid,
            )
        )
        next_id += 1
        inserted += 1
    return next_id, inserted


def _backfill_institution_type_and_stats_columns():
    """SQLite migrations may leave institution_type NULL until populated."""
    with db.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE schools SET institution_type = 'national_university' "
                "WHERE institution_type IS NULL OR institution_type = ''"
            )
        )


def seed_liberal_arts_if_missing() -> int:
    """
    Append liberal arts colleges from JSON when DB already had national data.
    Returns number of new rows inserted (0 if none).
    """
    if not os.path.isfile(LIBERAL_ARTS_JSON_PATH):
        return 0
    if School.query.filter_by(institution_type='liberal_arts').count() > 0:
        return 0

    with open(LIBERAL_ARTS_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    fallback_geo = {}
    if os.path.isfile(SEED_JSON_PATH):
        with open(SEED_JSON_PATH, 'r', encoding='utf-8') as f:
            fallback_geo = _name_to_geo_map(json.load(f))

    max_id = db.session.query(func.max(School.id)).scalar()
    next_id = (int(max_id) + 1) if max_id is not None else 0
    _, inserted = _append_schools_from_json_records(
        data, 'liberal_arts', next_id, geo_fallback_by_name=fallback_geo
    )
    if inserted:
        db.session.commit()
        print(f"Seeded {inserted} liberal arts college(s) from liberal_arts_colleges.json")
        _build_index()
        print("Search index rebuilt after seeding liberal arts data")
    return inserted


def sync_school_metadata_from_json() -> int:
    """
    For an existing database, copy city/state/coordinates (and optional stats)
    from national_university_data.json into matching rows by school_name.

    Keeps Phase 4 in sync without deleting data.db; add fields to JSON as you go.
    """
    if not os.path.isfile(SEED_JSON_PATH):
        return 0
    if School.query.count() == 0:
        return 0
    with open(SEED_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated_schools: set[str] = set()
    for school in data:
        name = school.get('school_name')
        if not name:
            continue
        city, state, lat, lng, acc, tuition, enrollment = _geo_bundle_from_school_json(school)
        niche_url = _optional_str(school.get('school_url'))
        if all(
            v is None
            for v in (city, state, lat, lng, acc, tuition, enrollment)
        ):
            continue

        row = School.query.filter_by(name=name).first()
        if not row:
            continue

        if city is not None and row.city != city:
            row.city = city
            updated_schools.add(name)
        if state is not None and row.state != state:
            row.state = state
            updated_schools.add(name)
        if lat is not None and _float_differs(row.latitude, lat):
            row.latitude = lat
            updated_schools.add(name)
        if lng is not None and _float_differs(row.longitude, lng):
            row.longitude = lng
            updated_schools.add(name)
        if acc is not None and _float_differs(row.acceptance_rate, acc):
            row.acceptance_rate = acc
            updated_schools.add(name)
        if tuition is not None and row.tuition != tuition:
            row.tuition = tuition
            updated_schools.add(name)
        if enrollment is not None and row.enrollment != enrollment:
            row.enrollment = enrollment
            updated_schools.add(name)
        if niche_url is not None and row.niche_url != niche_url:
            row.niche_url = niche_url
            updated_schools.add(name)

    if updated_schools:
        db.session.commit()
        print(f"Synced JSON metadata for {len(updated_schools)} school(s): {', '.join(sorted(updated_schools)[:10])}{'…' if len(updated_schools) > 10 else ''}")

    return len(updated_schools)


def sync_liberal_arts_metadata_from_json() -> int:
    """
    For existing liberal arts rows, copy city/state/coordinates (and optional stats)
    from liberal_arts_colleges.json into matching rows by school_name.
    """
    if not os.path.isfile(LIBERAL_ARTS_JSON_PATH):
        return 0
    if School.query.count() == 0:
        return 0

    with open(LIBERAL_ARTS_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated_schools: set[str] = set()
    for school in data:
        name = school.get('school_name')
        if not name:
            continue
        city, state, lat, lng, acc, tuition, enrollment = _geo_bundle_from_school_json(school)
        niche_url = _optional_str(school.get('school_url'))
        if all(
            v is None
            for v in (city, state, lat, lng, acc, tuition, enrollment)
        ):
            continue

        row = School.query.filter_by(name=name, institution_type='liberal_arts').first()
        if not row:
            continue

        if city is not None and row.city != city:
            row.city = city
            updated_schools.add(name)
        if state is not None and row.state != state:
            row.state = state
            updated_schools.add(name)
        if lat is not None and _float_differs(row.latitude, lat):
            row.latitude = lat
            updated_schools.add(name)
        if lng is not None and _float_differs(row.longitude, lng):
            row.longitude = lng
            updated_schools.add(name)
        if acc is not None and _float_differs(row.acceptance_rate, acc):
            row.acceptance_rate = acc
            updated_schools.add(name)
        if tuition is not None and row.tuition != tuition:
            row.tuition = tuition
            updated_schools.add(name)
        if enrollment is not None and row.enrollment != enrollment:
            row.enrollment = enrollment
            updated_schools.add(name)
        if niche_url is not None and row.niche_url != niche_url:
            row.niche_url = niche_url
            updated_schools.add(name)

    if updated_schools:
        db.session.commit()
        print(f"Synced liberal arts metadata for {len(updated_schools)} school(s): {', '.join(sorted(updated_schools)[:10])}{'…' if len(updated_schools) > 10 else ''}")

    return len(updated_schools)


def migrate_school_columns():
    """Add columns introduced after first DB creation (SQLite)."""
    inspector = inspect(db.engine)
    if 'schools' not in inspector.get_table_names():
        return
    cols = {c['name'] for c in inspector.get_columns('schools')}
    statements = []
    if 'city' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN city VARCHAR(128)')
    if 'state' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN state VARCHAR(64)')
    if 'latitude' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN latitude FLOAT')
    if 'longitude' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN longitude FLOAT')
    if 'acceptance_rate' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN acceptance_rate FLOAT')
    if 'tuition' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN tuition INTEGER')
    if 'enrollment' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN enrollment INTEGER')
    if 'reviews_json' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN reviews_json TEXT')
    if 'niche_url' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN niche_url VARCHAR(512)')
    if 'institution_type' not in cols:
        statements.append("ALTER TABLE schools ADD COLUMN institution_type VARCHAR(32)")
    if 'sat_25' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN sat_25 FLOAT')
    if 'sat_75' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN sat_75 FLOAT')
    if 'act_25' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN act_25 FLOAT')
    if 'act_75' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN act_75 FLOAT')
    if 'gpa_mid' not in cols:
        statements.append('ALTER TABLE schools ADD COLUMN gpa_mid FLOAT')
    if not statements:
        return
    with db.engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def init_db():
    with app.app_context():
        db.create_all()
        migrate_school_columns()
        _backfill_institution_type_and_stats_columns()

        if School.query.count() == 0:
            if not os.path.isfile(SEED_JSON_PATH):
                raise FileNotFoundError(
                    f"Seed data not found: {SEED_JSON_PATH}. "
                    "Place national_university_data.json under data/."
                )
            with open(SEED_JSON_PATH, 'r', encoding='utf-8') as f:
                national = json.load(f)
            fallback_geo = _name_to_geo_map(national)

            next_id, n_national = _append_schools_from_json_records(
                national, 'national_university', 0
            )
            n_liberal = 0
            if os.path.isfile(LIBERAL_ARTS_JSON_PATH):
                with open(LIBERAL_ARTS_JSON_PATH, 'r', encoding='utf-8') as f:
                    liberal = json.load(f)
                next_id, n_liberal = _append_schools_from_json_records(
                    liberal,
                    'liberal_arts',
                    next_id,
                    geo_fallback_by_name=fallback_geo,
                )

            db.session.commit()
            print(
                f"Database initialized with {n_national} national universities"
                + (f" and {n_liberal} liberal arts colleges" if n_liberal else "")
            )

            _build_index()
            print("TF-IDF index built")
        else:
            sync_school_metadata_from_json()
            seed_liberal_arts_if_missing()
            sync_liberal_arts_metadata_from_json()

init_db()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
