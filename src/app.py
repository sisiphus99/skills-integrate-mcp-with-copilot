"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import sqlite3
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

DB_FILE = current_dir / "activities.db"

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_db_connection():
    """Return a SQLite connection for the activity database."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create database tables and seed defaults when needed."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                UNIQUE(activity_name, email),
                FOREIGN KEY(activity_name) REFERENCES activities(name)
            )
            """
        )

        existing = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        if existing == 0:
            for name, attrs in DEFAULT_ACTIVITIES.items():
                conn.execute(
                    "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                    (name, attrs["description"], attrs["schedule"], attrs["max_participants"])
                )


def load_activities():
    """Load activities and participant lists from the database."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT name, description, schedule, max_participants FROM activities ORDER BY name").fetchall()
        activities = {}
        for row in rows:
            participants = [signup["email"] for signup in conn.execute(
                "SELECT email FROM signups WHERE activity_name = ? ORDER BY id",
                (row["name"],)
            ).fetchall()]
            activities[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": participants,
            }
        return activities


def activity_exists(activity_name: str):
    with get_db_connection() as conn:
        row = conn.execute("SELECT 1 FROM activities WHERE name = ?", (activity_name,)).fetchone()
        return row is not None


def signup_exists(activity_name: str, email: str):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM signups WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        ).fetchone()
        return row is not None


def activity_signup_count(activity_name: str):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM signups WHERE activity_name = ?",
            (activity_name,),
        ).fetchone()
        return row["count"]


initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    if not activity_exists(activity_name):
        raise HTTPException(status_code=404, detail="Activity not found")

    if signup_exists(activity_name, email):
        raise HTTPException(status_code=400, detail="Student is already signed up")

    max_participants = None
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        max_participants = row["max_participants"] if row else None

    current_count = activity_signup_count(activity_name)
    if max_participants is not None and current_count >= max_participants:
        raise HTTPException(status_code=400, detail="Activity is full")

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO signups (activity_name, email) VALUES (?, ?)",
            (activity_name, email),
        )
        conn.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    if not activity_exists(activity_name):
        raise HTTPException(status_code=404, detail="Activity not found")

    if not signup_exists(activity_name, email):
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM signups WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        )
        conn.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
