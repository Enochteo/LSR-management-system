"""Extension registry scaffold.

Keep global extension instances here so they can be initialized in `create_app()`.
"""

from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
 
# NOTE: These are initialized with app context in `init_extensions`.
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()

def init_extensions(app):
    """Bind all extension objects to the app.

    TODO:
    - Configure login settings (`login_view`, session protection).
    - Add optional extensions (migrate, csrf, rate limiter) when needed.
    """
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Optional UX redirect if auth blueprint is added.
    login_manager.login_view = "auth.login"
