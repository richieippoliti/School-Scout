from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text as sa_text

db = SQLAlchemy()

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    reviews_json = db.Column(db.Text, nullable=True)  # Stores reviews as JSON string
    avg_rating = db.Column(db.Float, nullable=False)
    niche_url = db.Column(db.String(512), nullable=True)
    institution_type = db.Column(
        db.String(32),
        nullable=False,
        server_default=sa_text("'national_university'"),
    )  # national_university | liberal_arts
    city = db.Column(db.String(128), nullable=True)
    state = db.Column(db.String(64), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    acceptance_rate = db.Column(db.Float, nullable=True)
    tuition = db.Column(db.Integer, nullable=True)
    enrollment = db.Column(db.Integer, nullable=True)
    # Optional admissions stats (seed when present in JSON); used for search filters
    sat_25 = db.Column(db.Float, nullable=True)
    sat_75 = db.Column(db.Float, nullable=True)
    act_25 = db.Column(db.Float, nullable=True)
    act_75 = db.Column(db.Float, nullable=True)
    gpa_mid = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'School {self.id}: {self.name}'
