from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    avg_rating = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'School {self.id}: {self.name}'
