from flask import Flask
from flask_login import LoginManager
from models.database import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fornowiamkeepingthisasthesecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from models.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from controllers.controllers import *

if __name__ == '__main__':
    app.run(debug=True)