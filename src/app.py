import json
import os
import pandas as pd
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import inspect, text

load_dotenv()
from flask_cors import CORS
from models import db, School
from routes import register_routes, _build_index

current_directory = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_directory)
SEED_JSON_PATH = os.path.join(project_root, 'data', 'national_university_data.json')
STATS_CSV_PATH = os.path.join(project_root, 'data', 'CLEANED_SchoolScouts.csv')

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

    if updated_schools:
        db.session.commit()
        print(f"Synced JSON metadata for {len(updated_schools)} school(s): {', '.join(sorted(updated_schools)[:10])}{'…' if len(updated_schools) > 10 else ''}")

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
        
    if 'sat_avg'    not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN sat_avg FLOAT')
    if 'act_avg'    not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN act_avg FLOAT')
    if 'hs_gpa_avg' not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN hs_gpa_avg FLOAT')
    if 'sat_ela_50' not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN sat_ela_50 FLOAT')
    if 'sat_ela_75' not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN sat_ela_75 FLOAT')
    if 'sat_math_50'not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN sat_math_50 FLOAT')
    if 'sat_math_75'not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN sat_math_75 FLOAT')
    if 'act_comp_50'not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN act_comp_50 FLOAT')
    if 'act_comp_75'not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN act_comp_75 FLOAT')
    if 'act_eng_50' not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN act_eng_50 FLOAT')
    if 'act_eng_75' not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN act_eng_75 FLOAT')
    if 'act_math_50'not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN act_math_50 FLOAT')
    if 'act_math_75'not in cols: 
        statements.append('ALTER TABLE schools ADD COLUMN act_math_75 FLOAT')
    if not statements:
        return
    with db.engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
            
_CSV_TO_MODEL: dict[str, str] = {
    'satAvg':          'sat_avg',
    'actAvg':          'act_avg',
    'hsGpaAvg':        'hs_gpa_avg',
    'acceptanceRate':  'acceptance_rate',  # also in JSON; CSV wins if both present
    'satEla50':        'sat_ela_50',
    'satEla75':        'sat_ela_75',
    'satMath50':       'sat_math_50',
    'satMath75':       'sat_math_75',
    'actComp50':       'act_comp_50',
    'actComp75':       'act_comp_75',
    'actEng50':        'act_eng_50',
    'actEng75':        'act_eng_75',
    'actMath50':       'act_math_50',
    'actMath75':       'act_math_75',
}

def sync_numeric_stats_from_csv() -> int:
    """
    Load CLEANED_SchoolScouts.csv and write SAT/ACT/GPA stats into the
    schools table, matching rows by institution name.
 
    - Skips rows where every stat column is NaN (no data to write).
    - Skips schools not present in the database (no new rows created).
    - Only commits when at least one value actually changed.
    - Safe to call on every startup — idempotent.
    """
    if not os.path.isfile(STATS_CSV_PATH):
        print(f"Stats CSV not found at {STATS_CSV_PATH}, skipping numeric sync")
        return 0
    if School.query.count() == 0:
        return 0
 
    df = pd.read_csv(STATS_CSV_PATH)
 
    stat_cols = list(_CSV_TO_MODEL.keys())
    # Drop rows where every stat column is NaN — nothing useful to write
    df = df.dropna(subset=stat_cols, how='all')
 
    updated_count = 0
    for _, csv_row in df.iterrows():
        name = str(csv_row.get('institution', '')).strip()
        if not name:
            continue
 
        row = School.query.filter_by(name=name).first()
        if not row:
            continue  # school not in DB — don't create new records here
 
        changed = False
        for csv_col, model_attr in _CSV_TO_MODEL.items():
            new_val = _optional_float(csv_row.get(csv_col))
            if new_val is None:
                continue  # NaN in CSV — leave whatever is already stored
            if _float_differs(getattr(row, model_attr, None), new_val):
                setattr(row, model_attr, new_val)
                changed = True
 
        if changed:
            updated_count += 1
 
    if updated_count:
        db.session.commit()
        print(f"Synced CSV numeric stats for {updated_count} school(s)")
    else:
        print("CSV numeric stats: no changes detected")
 
    return updated_count

def init_db():
    with app.app_context():
        db.create_all()
        migrate_school_columns()

        if School.query.count() == 0:
            if not os.path.isfile(SEED_JSON_PATH):
                raise FileNotFoundError(
                    f"Seed data not found: {SEED_JSON_PATH}. "
                    "Place national_university_data.json under data/."
                )
            with open(SEED_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            schools_loaded = 0
            for i, school in enumerate(data):
                reviews = school.get('reviews', [])
                if not school.get('ai_summary'):
                    continue  # skip schools without AI summary

                avg_rating = sum(r['rating'] for r in reviews) / len(reviews)
                city, state, lat, lng, acc, tuition, enrollment = _geo_bundle_from_school_json(school)

                db.session.add(School(
                    id=i,
                    name=school['school_name'],
                    summary=school['ai_summary'],
                    reviews_json=json.dumps(reviews),
                    avg_rating=round(avg_rating, 2),
                    city=city,
                    state=state,
                    latitude=lat,
                    longitude=lng,
                    acceptance_rate=acc,
                    tuition=tuition,
                    enrollment=enrollment,
                ))
                schools_loaded += 1

            db.session.commit()
            print(f"Database initialized with {schools_loaded} schools")

            _build_index()
            print("TF-IDF index built")
        else:
            sync_school_metadata_from_json()

init_db()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
