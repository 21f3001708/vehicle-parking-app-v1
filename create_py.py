import os
from datetime import datetime
from app import app, db
from models.models import User, ParkingLot, ParkingSpot, Reservation

# To find the models
from models import models

# Path of database file
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parking.db')

def setup_database():
    with app.app_context():
        # Dropping all tables and then creating when starting
        db.drop_all()
        db.create_all()

        # Creating the admin user (as it is predefined, requires no registration)
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin = User(
                username='admin',
                password='admin_password',
                full_name='Admin User',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")

# Commenting the below code as it is not necessary to check whether the db exists or not!
# if __name__ == '__main__':
#     if not os.path.exists(db_path):
#         setup_database()
#         print("Database created and admin user added.")
#     else:
#         print("Database already exists. Running setup to ensure schema is updated and admin exists.")
#         setup_database()

if __name__ == '__main__':
    setup_database()