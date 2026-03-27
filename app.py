from flask import Flask

from config import DevelopmentConfig
from extensions import init_extensions, db
from routes import register_blueprints

def create_app(config_object=DevelopmentConfig):
    """Create and configure the Flask application instance.

    TODO (Phase 0):
    - Allow selecting config via environment variable.
    - Add production-safe logging setup.
    - Add error handler registration.
    """
    app = Flask(__name__)
    app.config.from_object(config_object)
    # Initialize all extension objects (db, login manager, mail, etc.).
    init_extensions(app)

    # Register all route blueprints (auth, attendance, admin, qr).
    register_blueprints(app)
    from database.models import Student, Room, AttendanceRecord
    @app.get("/")
    def home():
        """Minimal health-like landing page for Phase 0 verification."""
        return "Hello, world! Smart Digital Library scaffold is running."

    return app


app = create_app()


if __name__ == "__main__":
    # Local-only run path; prefer `flask run` with FLASK_APP=app:create_app.
    app.run(debug=True)