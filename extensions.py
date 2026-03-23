"""Extension registry scaffold.

Keep global extension instances here so they can be initialized in `create_app()`.
"""

from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
 
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()

def init_extensions(app):
   
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
