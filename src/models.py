from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    avg_rating = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(128), nullable=True)
    state = db.Column(db.String(64), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    acceptance_rate = db.Column(db.Float, nullable=True)
    tuition = db.Column(db.Integer, nullable=True)
    enrollment = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'School {self.id}: {self.name}'
