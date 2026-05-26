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
    "classification": "VARCHAR(80)",
    "why_saved": "TEXT",
    "reject_reason": "TEXT",
    "portal_domain": "VARCHAR(255)",
    "discovery_candidate_id": "INTEGER",
}

PORTAL_COLUMNS = {
    "canonical_domain": "VARCHAR(255)",
    "domain_status": "VARCHAR(50) DEFAULT 'active'",
    "platform_key": "VARCHAR(80)",
}

SCHOLARSHIP_VISIBILITY_COLUMNS = {
    "visibility_status": "VARCHAR(50) DEFAULT 'active'",
    "trusted_platform_key": "VARCHAR(80)",
}

TELEGRAM_COLUMNS = {
    "last_error_code": "INTEGER",
    "last_error_description": "TEXT",
}

DOCUMENT_COLUMNS = {
    "original_filename": "VARCHAR(500)",
    "storage_path": "VARCHAR(1000)",
    "extracted_text": "TEXT",
    "extraction_status": "VARCHAR(50) DEFAULT 'pending'",
    "processing_status": "VARCHAR(50) DEFAULT 'uploaded'",
    "source_type": "VARCHAR(80) DEFAULT 'other'",
    "extraction_error": "TEXT",
}

PROFILE_GRAPH_COLUMNS = {
    "details": "TEXT",
    "status": "VARCHAR(50) DEFAULT 'needs_review'",
    "canonical_key": "VARCHAR(300)",
    "importance_score": "FLOAT DEFAULT 0.5",
    "used_in_essays_count": "INTEGER DEFAULT 0",
    "legacy_story_id": "INTEGER",
}

GMAIL_MESSAGE_COLUMNS = {
    "scan_error": "TEXT",
}

PORTAL_RUN_COLUMNS = {
    "latest_screenshot_path": "VARCHAR(1000)",
    "browser_mode": "VARCHAR(50)",
}

PORTAL_SESSION_COLUMNS = {
    "storage_state_path": "VARCHAR(1000)",
    "last_validated_at": "TIMESTAMP",
}

PORTAL_OPPORTUNITY_COLUMNS = {
    "quality_status": "VARCHAR(50) DEFAULT 'accepted'",
    "quality_reason": "TEXT",
    "quality_score": "INTEGER DEFAULT 0",
    "link_classification": "VARCHAR(80)",
    "canonical_url": "VARCHAR(1000)",
}


def _add_columns(table: str, columns: dict) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for col, col_type in columns.items():
            if col in existing:
                continue
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"))
            else:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                except Exception:
                    pass


def run_migrations() -> None:
    _add_columns("scholarships", SCHOLARSHIP_COLUMNS)
    _add_columns("portals", PORTAL_COLUMNS)
    _add_columns("scholarships", SCHOLARSHIP_VISIBILITY_COLUMNS)
    _add_columns("telegram_user_config", TELEGRAM_COLUMNS)
    _add_columns("documents", DOCUMENT_COLUMNS)
    _add_columns("profile_graph_nodes", PROFILE_GRAPH_COLUMNS)
    _add_columns("gmail_messages", GMAIL_MESSAGE_COLUMNS)
    _add_columns("portal_runs", PORTAL_RUN_COLUMNS)
    _add_columns("portal_sessions", PORTAL_SESSION_COLUMNS)
    _add_columns("portal_opportunities", PORTAL_OPPORTUNITY_COLUMNS)
