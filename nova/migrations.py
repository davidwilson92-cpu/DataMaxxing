from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine, inspect, text


MIGRATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("20260918_default_brand_name", ("default_brand_name VARCHAR(100) NOT NULL DEFAULT 'My brand'",)),
    ("20260914_auth_version", ("auth_version INTEGER NOT NULL DEFAULT 0",)),
    (
        "20260811_user_signup_profile",
        (
            "display_name VARCHAR(160) NOT NULL DEFAULT ''",
            "country_code VARCHAR(2) NOT NULL DEFAULT ''",
            "email_verified_at TIMESTAMP NULL",
            "last_login_at TIMESTAMP NULL",
            "updated_at TIMESTAMP NULL",
            "terms_accepted_at TIMESTAMP NULL",
            "marketing_consent BOOLEAN NOT NULL DEFAULT FALSE",
            "marketing_consent_at TIMESTAMP NULL",
        ),
    ),
)


def _user_columns(engine: Engine) -> set[str]:
    inspector = inspect(engine)
    if "nova_users" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("nova_users")}


def run_migrations(engine: Engine, migrations: Iterable[tuple[str, tuple[str, ...]]] = MIGRATIONS) -> None:
    """Apply small, forward-only schema migrations without a deployment-time dependency."""
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS zova_schema_migrations (version VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMP NOT NULL)"))

    for version, additions in migrations:
        with engine.begin() as connection:
            applied = connection.execute(
                text("SELECT 1 FROM zova_schema_migrations WHERE version = :version"),
                {"version": version},
            ).first()
        if applied:
            continue

        columns = _user_columns(engine)
        with engine.begin() as connection:
            for definition in additions:
                column_name = definition.split(" ", 1)[0]
                if column_name not in columns:
                    connection.execute(text(f"ALTER TABLE nova_users ADD COLUMN {definition}"))
            connection.execute(
                text("INSERT INTO zova_schema_migrations (version, applied_at) VALUES (:version, CURRENT_TIMESTAMP)"),
                {"version": version},
            )

    additions = {'nova_drafts': ("workspace_json TEXT NOT NULL DEFAULT '{}'", "revision INTEGER NOT NULL DEFAULT 0")}
    for table in ('nova_drafts', 'nova_social_connections', 'nova_oauth_states', 'zova_publish_reviews',
                  'zova_publications', 'nova_media_assets', 'nova_scheduled_posts', 'nova_activity'):
        additions[table] = additions.get(table, ()) + ("brand_id INTEGER NOT NULL DEFAULT 0",)
    for table, definitions in additions.items():
        columns = {c['name'] for c in inspect(engine).get_columns(table)}
        with engine.begin() as connection:
            for definition in definitions:
                if definition.split()[0] not in columns:
                    connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {definition}'))
