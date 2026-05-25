"""Safe additive schema updates for existing Railway Postgres / SQLite DBs."""
from sqlalchemy import inspect, text
from app.database import engine


SCHOLARSHIP_COLUMNS = {
    "provider": "VARCHAR(500)",
    "application_url": "VARCHAR(1000)",
    "discovered_at": "TIMESTAMP",
    "search_query_used": "VARCHAR(500)",
    "extraction_confidence": "FLOAT",
    "portal_login_required": "VARCHAR(20)",
    "manual_step_likely": "BOOLEAN DEFAULT FALSE",
    "low_trust_reason": "TEXT",
    "normalized_url": "VARCHAR(1000)",
    "dedupe_key": "VARCHAR(600)",
    "gpa_requirement": "VARCHAR(100)",
    "user_edited": "BOOLEAN DEFAULT FALSE",
}


def run_migrations() -> None:
    insp = inspect(engine)
    if "scholarships" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("scholarships")}
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for col, col_type in SCHOLARSHIP_COLUMNS.items():
            if col in existing:
                continue
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE scholarships ADD COLUMN IF NOT EXISTS {col} {col_type}"))
            else:
                try:
                    conn.execute(text(f"ALTER TABLE scholarships ADD COLUMN {col} {col_type}"))
                except Exception:
                    pass
