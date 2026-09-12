"""Resets the database and populates it with demo users, 8 realistic
projects (each with tasks and cost/schedule history), then trains the AI
prediction model and runs it against every seeded project.

Run with:  python seed.py
"""
from app import create_app
from app.extensions import db
from app.models import User, Project, Task, ProjectSnapshot
from app.seed_data import reset_and_seed


def main():
    app = create_app()
    with app.app_context():
        print("Dropping and recreating all tables...")
        print("Training AI prediction model on synthetic historical data...")
        print("Creating users and 8 demo projects with tasks and history...")
        reset_and_seed()

        print("\nDone. Seeded:")
        print(f"  Users: {User.query.count()}")
        print(f"  Projects: {Project.query.count()}")
        print(f"  Tasks: {Task.query.count()}")
        print(f"  Snapshots: {ProjectSnapshot.query.count()}")
        print("\nLogin with:")
        print("  Admin:   admin@projectai.com / Admin@123")
        print("  Manager: priya.manager@projectai.com / Manager@123")


if __name__ == "__main__":
    main()
