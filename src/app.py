"""
Slalom Capabilities Management System API

A FastAPI application that enables Slalom consultants to register their
capabilities and manage consulting expertise across the organization.
"""

import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

APP_TITLE = "Slalom Capabilities Management API"
APP_DESCRIPTION = "API for managing consulting capabilities and consultant expertise"

current_dir = Path(__file__).parent

INITIAL_CAPABILITIES = {
    "Cloud Architecture": {
        "description": "Design and implement scalable cloud solutions using AWS, Azure, and GCP",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["AWS Solutions Architect", "Azure Architect Expert"],
        "industry_verticals": ["Healthcare", "Financial Services", "Retail"],
        "capacity": 40,  # hours per week available across team
        "consultants": ["alice.smith@slalom.com", "bob.johnson@slalom.com"]
    },
    "Data Analytics": {
        "description": "Advanced data analysis, visualization, and machine learning solutions",
        "practice_area": "Technology", 
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Tableau Desktop Specialist", "Power BI Expert", "Google Analytics"],
        "industry_verticals": ["Retail", "Healthcare", "Manufacturing"],
        "capacity": 35,
        "consultants": ["emma.davis@slalom.com", "sophia.wilson@slalom.com"]
    },
    "DevOps Engineering": {
        "description": "CI/CD pipeline design, infrastructure automation, and containerization",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"], 
        "certifications": ["Docker Certified Associate", "Kubernetes Admin", "Jenkins Certified"],
        "industry_verticals": ["Technology", "Financial Services"],
        "capacity": 30,
        "consultants": ["john.brown@slalom.com", "olivia.taylor@slalom.com"]
    },
    "Digital Strategy": {
        "description": "Digital transformation planning and strategic technology roadmaps",
        "practice_area": "Strategy",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Digital Transformation Certificate", "Agile Certified Practitioner"],
        "industry_verticals": ["Healthcare", "Financial Services", "Government"],
        "capacity": 25,
        "consultants": ["liam.anderson@slalom.com", "noah.martinez@slalom.com"]
    },
    "Change Management": {
        "description": "Organizational change leadership and adoption strategies",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Prosci Certified", "Lean Six Sigma Black Belt"],
        "industry_verticals": ["Healthcare", "Manufacturing", "Government"],
        "capacity": 20,
        "consultants": ["ava.garcia@slalom.com", "mia.rodriguez@slalom.com"]
    },
    "UX/UI Design": {
        "description": "User experience design and digital product innovation",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Adobe Certified Expert", "Google UX Design Certificate"],
        "industry_verticals": ["Retail", "Healthcare", "Technology"],
        "capacity": 30,
        "consultants": ["amelia.lee@slalom.com", "harper.white@slalom.com"]
    },
    "Cybersecurity": {
        "description": "Information security strategy, risk assessment, and compliance",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["CISSP", "CISM", "CompTIA Security+"],
        "industry_verticals": ["Financial Services", "Healthcare", "Government"],
        "capacity": 25,
        "consultants": ["ella.clark@slalom.com", "scarlett.lewis@slalom.com"]
    },
    "Business Intelligence": {
        "description": "Enterprise reporting, data warehousing, and business analytics",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Microsoft BI Certification", "Qlik Sense Certified"],
        "industry_verticals": ["Retail", "Manufacturing", "Financial Services"],
        "capacity": 35,
        "consultants": ["james.walker@slalom.com", "benjamin.hall@slalom.com"]
    },
    "Agile Coaching": {
        "description": "Agile transformation and team coaching for scaled delivery",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Certified Scrum Master", "SAFe Agilist", "ICAgile Certified"],
        "industry_verticals": ["Technology", "Financial Services", "Healthcare"],
        "capacity": 20,
        "consultants": ["charlotte.young@slalom.com", "henry.king@slalom.com"]
    }
}


INITIAL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS capabilities (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    practice_area TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    skill_levels_json TEXT NOT NULL,
    certifications_json TEXT NOT NULL,
    industry_verticals_json TEXT NOT NULL,
    display_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS consultant_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capability_name TEXT NOT NULL,
    email TEXT NOT NULL,
    UNIQUE(capability_name, email),
    FOREIGN KEY (capability_name) REFERENCES capabilities(name) ON DELETE CASCADE
);
"""


class CapabilityStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(INITIAL_SCHEMA_SQL)

            migration_exists = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("001_initial_schema",),
            ).fetchone()
            if migration_exists is None:
                connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)",
                    ("001_initial_schema",),
                )

            capability_count = connection.execute(
                "SELECT COUNT(*) FROM capabilities"
            ).fetchone()[0]
            if capability_count == 0:
                self._seed_capabilities(connection)

            connection.commit()

    def get_capabilities(self) -> dict[str, dict]:
        with self._connect() as connection:
            capability_rows = connection.execute(
                """
                SELECT
                    name,
                    description,
                    practice_area,
                    capacity,
                    skill_levels_json,
                    certifications_json,
                    industry_verticals_json
                FROM capabilities
                ORDER BY display_order, name
                """
            ).fetchall()

            consultant_rows = connection.execute(
                """
                SELECT capability_name, email
                FROM consultant_registrations
                ORDER BY capability_name, id
                """
            ).fetchall()

        consultants_by_capability: dict[str, list[str]] = {}
        for consultant_row in consultant_rows:
            consultants_by_capability.setdefault(
                consultant_row["capability_name"], []
            ).append(consultant_row["email"])

        capabilities: dict[str, dict] = {}
        for row in capability_rows:
            capabilities[row["name"]] = {
                "description": row["description"],
                "practice_area": row["practice_area"],
                "skill_levels": json.loads(row["skill_levels_json"]),
                "certifications": json.loads(row["certifications_json"]),
                "industry_verticals": json.loads(row["industry_verticals_json"]),
                "capacity": row["capacity"],
                "consultants": consultants_by_capability.get(row["name"], []),
            }

        return capabilities

    def register_consultant(self, capability_name: str, email: str) -> None:
        with self._connect() as connection:
            self._require_capability(connection, capability_name)

            existing_row = connection.execute(
                """
                SELECT 1
                FROM consultant_registrations
                WHERE capability_name = ? AND email = ?
                """,
                (capability_name, email),
            ).fetchone()
            if existing_row is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Consultant is already registered for this capability",
                )

            connection.execute(
                """
                INSERT INTO consultant_registrations(capability_name, email)
                VALUES (?, ?)
                """,
                (capability_name, email),
            )
            connection.commit()

    def unregister_consultant(self, capability_name: str, email: str) -> None:
        with self._connect() as connection:
            self._require_capability(connection, capability_name)

            existing_row = connection.execute(
                """
                SELECT id
                FROM consultant_registrations
                WHERE capability_name = ? AND email = ?
                """,
                (capability_name, email),
            ).fetchone()
            if existing_row is None:
                raise HTTPException(
                    status_code=400,
                    detail="Consultant is not registered for this capability",
                )

            connection.execute(
                "DELETE FROM consultant_registrations WHERE id = ?",
                (existing_row["id"],),
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _require_capability(
        self, connection: sqlite3.Connection, capability_name: str
    ) -> None:
        capability_row = connection.execute(
            "SELECT 1 FROM capabilities WHERE name = ?",
            (capability_name,),
        ).fetchone()
        if capability_row is None:
            raise HTTPException(status_code=404, detail="Capability not found")

    def _seed_capabilities(self, connection: sqlite3.Connection) -> None:
        for index, (name, details) in enumerate(INITIAL_CAPABILITIES.items(), start=1):
            connection.execute(
                """
                INSERT INTO capabilities(
                    name,
                    description,
                    practice_area,
                    capacity,
                    skill_levels_json,
                    certifications_json,
                    industry_verticals_json,
                    display_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    details["description"],
                    details["practice_area"],
                    details["capacity"],
                    json.dumps(details["skill_levels"]),
                    json.dumps(details["certifications"]),
                    json.dumps(details["industry_verticals"]),
                    index,
                ),
            )

            for consultant_email in details["consultants"]:
                connection.execute(
                    """
                    INSERT INTO consultant_registrations(capability_name, email)
                    VALUES (?, ?)
                    """,
                    (name, consultant_email),
                )


def get_default_db_path() -> Path:
    configured_path = os.getenv("CAPABILITIES_DB_PATH")
    if configured_path:
        return Path(configured_path)

    return current_dir / "data" / "capabilities.sqlite"


def create_app(db_path: Path | None = None) -> FastAPI:
    app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION)
    app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

    store = CapabilityStore(db_path or get_default_db_path())
    store.initialize()
    app.state.store = store

    @app.get("/")
    def root():
        return RedirectResponse(url="/static/index.html")

    @app.get("/capabilities")
    def get_capabilities(request: Request):
        return request.app.state.store.get_capabilities()

    @app.post("/capabilities/{capability_name}/register")
    def register_for_capability(capability_name: str, email: str, request: Request):
        request.app.state.store.register_consultant(capability_name, email)
        return {"message": f"Registered {email} for {capability_name}"}

    @app.delete("/capabilities/{capability_name}/unregister")
    def unregister_from_capability(capability_name: str, email: str, request: Request):
        request.app.state.store.unregister_consultant(capability_name, email)
        return {"message": f"Unregistered {email} from {capability_name}"}

    return app


app = create_app()
