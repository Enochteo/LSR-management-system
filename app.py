"""Application factory.

Usage:
    flask run                        # local dev
    flask create-admin               # create first admin user
    flask run-enforcement            # manual enforcement pass (for cron)
    flask seed-rooms                 # seed sample rooms for development
"""

import os

import click
from flask import Flask

from config import DevelopmentConfig, ProductionConfig, TestingConfig
from extensions import db, init_extensions, login_manager
from routes import register_blueprints

_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def create_app(config_object=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Select config from env or explicit argument.
    if config_object is None:
        env = os.getenv("FLASK_ENV", "development")
        config_object = _CONFIG_MAP.get(env, DevelopmentConfig)
    app.config.from_object(config_object)

    init_extensions(app)
    register_blueprints(app)
    _register_user_loader()
    _register_cli_commands(app)
    _register_error_handlers(app)

    return app


def _register_user_loader():
    """Tell Flask-Login how to reload a user from the session."""
    from database.models import Student

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Student, int(user_id))


def _register_cli_commands(app):
    """Attach management CLI commands to the app."""

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Full name")
    @click.option("--email", prompt="Email")
    @click.option("--student-id", prompt="Student/staff ID", default="")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, student_id, password):
        """Create or promote a user to admin."""
        from database.models import Student

        student = db.session.execute(
            db.select(Student).where(Student.email == email)
        ).scalar_one_or_none()

        if student:
            student.is_admin = True
            student.set_password(password)
            click.echo(f"Promoted existing user '{email}' to admin.")
        else:
            student = Student(
                full_name=name,
                email=email,
                student_id=student_id or None,
                is_admin=True,
            )
            student.set_password(password)
            db.session.add(student)
            click.echo(f"Created admin user '{email}'.")

        db.session.commit()

    @app.cli.command("run-enforcement")
    def run_enforcement():
        """Run one session enforcement pass (suitable for system cron)."""
        from cron.cron_job import run_enforcement_cycle

        run_enforcement_cycle()
        click.echo("Enforcement cycle complete.")

    @app.cli.command("seed-rooms")
    def seed_rooms():
        """Insert sample study rooms for development."""
        from database.models import Room

        sample_rooms = [
            {"name": "Study Room A", "room_code": "ROOM-A", "capacity": 6},
            {"name": "Study Room B", "room_code": "ROOM-B", "capacity": 6},
            {"name": "Quiet Zone C", "room_code": "ROOM-C", "capacity": 4},
            {"name": "Group Room D", "room_code": "ROOM-D", "capacity": 6},
        ]
        added = 0
        for data in sample_rooms:
            existing = db.session.execute(
                db.select(Room).where(Room.room_code == data["room_code"])
            ).scalar_one_or_none()
            if not existing:
                db.session.add(Room(**data))
                added += 1

        db.session.commit()
        click.echo(f"Seeded {added} room(s).")


def _register_error_handlers(app):
    """Register HTTP error page handlers."""
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
