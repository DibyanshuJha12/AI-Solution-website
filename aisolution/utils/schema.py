from __future__ import annotations

from flask import current_app
from sqlalchemy import inspect, text

from ..extensions import db


def synchronize_schema() -> None:
    """Create missing tables and backfill critical columns for older project databases."""
    db.create_all()

    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name
    patches = schema_patches(dialect)

    for table_name, columns in patches.items():
        if table_name not in inspector.get_table_names():
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, ddl in columns:
            if column_name in existing_columns:
                continue
            current_app.logger.info("Applying schema patch: %s.%s", table_name, column_name)
            try:
                db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
                db.session.commit()
            except Exception as error:
                db.session.rollback()
                if "duplicate column" in str(error).lower():
                    current_app.logger.debug("Schema patch already applied: %s.%s", table_name, column_name)
                    existing_columns.add(column_name)
                    continue
                raise
            existing_columns.add(column_name)

    db.session.commit()


def schema_patches(dialect: str) -> dict[str, list[tuple[str, str]]]:
    timestamp_type = "TIMESTAMP"
    boolean_type = "BOOLEAN"
    json_type = "JSON" if dialect == "postgresql" else "TEXT"

    return {
        "staff_users": [
            ("password_changed_at", f"{timestamp_type} DEFAULT CURRENT_TIMESTAMP NOT NULL"),
            ("last_login_ip", "VARCHAR(80)"),
            ("failed_login_count", "INTEGER DEFAULT 0 NOT NULL"),
        ],
        "public_users": [
            ("password_changed_at", f"{timestamp_type} DEFAULT CURRENT_TIMESTAMP NOT NULL"),
            ("company", "VARCHAR(160)"),
            ("accepted_privacy", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("accepted_privacy_at", timestamp_type),
            ("last_login_at", timestamp_type),
            ("last_login_ip", "VARCHAR(80)"),
            ("failed_login_count", "INTEGER DEFAULT 0 NOT NULL"),
        ],
        "services": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
        ],
        "events": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
        ],
        "rsvps": [
            ("job_title", "VARCHAR(120)"),
            ("preferred_session", "VARCHAR(120)"),
            ("special_requirements", "TEXT"),
            ("message", "TEXT"),
        ],
        "inquiries": [
            ("subject", "VARCHAR(180) DEFAULT 'General Inquiry' NOT NULL"),
        ],
        "blog_posts": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
            ("content", "TEXT DEFAULT '' NOT NULL"),
            ("featured", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("meta_title", "VARCHAR(255)"),
            ("meta_description", "VARCHAR(320)"),
        ],
        "testimonials": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
        ],
        "case_studies": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
            ("key_features", f"{json_type}"),
        ],
        "jobs": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
        ],
        "faq_items": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
        ],
        "team_members": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
        ],
        "media_assets": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
        ],
        "auth_session_logs": [
            ("location_label", "VARCHAR(255)"),
            ("latitude", "FLOAT"),
            ("longitude", "FLOAT"),
            ("camera_consent", "VARCHAR(40) DEFAULT 'not-requested' NOT NULL"),
            ("camera_image_path", "VARCHAR(255)"),
        ],
        "site_settings": [
            ("archived", f"{boolean_type} DEFAULT FALSE NOT NULL"),
            ("published_at", timestamp_type),
            ("value_type", "VARCHAR(30) DEFAULT 'text' NOT NULL"),
            ("description", "VARCHAR(255)"),
        ],
        "activity_logs": [
            ("details", f"{json_type}"),
        ],
    }
