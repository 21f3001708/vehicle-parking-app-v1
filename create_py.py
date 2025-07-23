import os
from werkzeug.security import generate_password_hash
from app import app
from database import db
from models.models import User

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parking.db')

def setup_database():
    with app.app_context():
        db.drop_all()
        print("Dropped all tables")

        db.create_all()
        print("Created all tables")

        # Creating the admin user (as it is predefined, requires no registration)
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            hashed_password = generate_password_hash('admin_password', method='pbkdf2:sha256')
            admin = User(
                username='admin',
                password=hashed_password,
                full_name='Admin User',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    setup_database()
    print("Database setup complete")