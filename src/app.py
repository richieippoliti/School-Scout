import json
import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()
from flask_cors import CORS
from models import db, School
from routes import register_routes

# src/ directory and project root (one level up)
current_directory = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_directory)

# Serve React build files from <project_root>/frontend/dist
app = Flask(__name__,
    static_folder=os.path.join(project_root, 'frontend', 'dist'),
    static_url_path='')
CORS(app)

# Configure SQLite database - using 3 slashes for relative path
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)

# Register routes
register_routes(app)

def init_db():
    with app.app_context():
        db.create_all()

        if School.query.count() == 0:
            json_file_path = os.path.join(project_root, 'data', '30schools_reviews.json')
            with open(json_file_path, 'r') as f:
                data = json.load(f)

            schools_loaded = 0
            for i, school in enumerate(data):
                reviews = school.get('reviews', [])
                if not reviews or not school.get('ai_summary'):
                    continue  # skipping schools w no summary for now while greg scrapes more

                avg_rating = sum(r['rating'] for r in reviews) / len(reviews)

                db.session.add(School(
                    id=i,
                    name=school['school_name'],
                    summary=school['ai_summary'],
                    avg_rating=round(avg_rating, 2)
                ))
                schools_loaded += 1

            db.session.commit()
            print(f"Database initialized with {schools_loaded} schools")

init_db()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
