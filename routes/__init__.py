"""Blueprint registration scaffold.

This module centralizes blueprint imports and registration order.
"""

from .admin_routes import admin_bp
from .attendance_routes import attendance_bp
from .auth_routes import auth_bp
from .qr_routes import qr_bp


def register_blueprints(app):
    """Attach all blueprints to the Flask app instance.

    TODO:
    - Add URL prefixes if route namespaces become large.
    - Add API-versioning strategy if JSON APIs are introduced.
    """
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(qr_bp)
