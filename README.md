# LSR Management System

## Short Summary
LSR Management System is a Flask-based web application for managing library study room sign-ins with QR codes, enforcing session limits, sending reminders, and giving administrators a dashboard for room usage and attendance review.

## Features
- QR-based room sign-in
- 3-hour session enforcement with automated sign-out
- Email alerts for upcoming session expiry
- Admin dashboard for active sessions and daily logs
- CSV and PDF reporting support

## Tech Stack
- Python 3.11+
- Flask
- Flask-SQLAlchemy and Flask-Migrate
- Alembic migrations
- Jinja2 templates and static assets

## Project Structure
- app.py - Flask application factory and CLI commands
- config.py - Configuration classes
- extensions.py - Flask extension initialization
- database/ - ORM models
- routes/ - Blueprint routes
- services/ - Business logic
- cron/ - Session enforcement job
- templates/ - HTML templates
- static/ - CSS, JavaScript, and assets
- migrations/ - Alembic migration files

## Local Setup
1. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

3. Set your environment variables. At minimum, configure your Flask app and database connection.

4. Run database migrations.

   ```bash
   flask db upgrade
   ```

5. Start the application.

   ```bash
   flask run
   ```

## CLI Commands
The app exposes a few utility commands through app.py:
- flask create-admin
- flask create-superuser
- flask run-enforcement
- flask seed-rooms

## Deployment Notes
If you deploy to Railway with Docker, make sure the build image includes system packages required by native Python dependencies. The repository includes lsr-app.dockerfile for that purpose.

## License
No license file is included yet.
