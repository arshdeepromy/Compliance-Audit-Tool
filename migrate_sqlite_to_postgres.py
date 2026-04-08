"""Migrate all data from SQLite to PostgreSQL.

Usage (run from inside the web container or locally):
    python migrate_sqlite_to_postgres.py

Reads from the SQLite database at instance/totika.db and writes to the
PostgreSQL database specified by DATABASE_URL env var.

The script:
  1. Connects to both databases
  2. Reads all rows from every table in SQLite (except alembic_version, sqlite_sequence)
  3. Inserts them into PostgreSQL (which should already have the schema via Alembic)
  4. Resets PostgreSQL sequences to match the max IDs
  5. Verifies row counts match
"""

import os
import sys
import sqlite3
from datetime import datetime, date

import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect, MetaData

SQLITE_PATH = os.environ.get(
    "SQLITE_PATH",
    os.path.join(os.path.dirname(__file__), "instance", "totika.db"),
)
POSTGRES_URL = os.environ.get(
    "DATABASE_URL", "postgresql://totika:totika-dev-password@localhost:5436/totika"
)

# Tables to skip during migration
SKIP_TABLES = {"alembic_version", "sqlite_sequence"}

# Table insertion order — respects foreign key dependencies
TABLE_ORDER = [
    "user",
    "session",
    "user_passkey",
    "audit_template",
    "template_section",
    "template_criterion",
    "criterion_scoring_anchor",
    "criterion_evidence_item",
    "audit",
    "audit_score",
    "evidence_check_state",
    "audit_sign_off",
    "corrective_action",
    "action_evidence",
    "evidence_attachment",
    "branding_settings",
    "smtp_settings",
    "activity_log",
    "seed_file_tracker",
    "scoping_question",
    "scoping_rule",
    "scoping_profile",
    "criterion_applicability",
    "risk_category",
    "risk",
    "risk_mitigation",
    "risk_review",
]


def get_sqlite_tables(conn):
    """Return list of user tables in SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cursor.fetchall() if r[0] not in SKIP_TABLES]


def get_sqlite_rows(conn, table):
    """Return all rows from a SQLite table as list of dicts."""
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM "{table}"')
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_column_info(pg_engine, table_name):
    """Get column types from PostgreSQL for type conversion."""
    insp = inspect(pg_engine)
    columns = insp.get_columns(table_name)
    return {col["name"]: col["type"] for col in columns}


def convert_value(value, col_type):
    """Convert a SQLite value to the appropriate Python type for PostgreSQL."""
    if value is None:
        return None

    type_name = type(col_type).__name__

    if type_name == "BOOLEAN" or type_name == "Boolean":
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ("1", "true", "t", "yes")
        return bool(value)

    if type_name in ("DATETIME", "DateTime"):
        if isinstance(value, str):
            # Try common datetime formats
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return value

    if type_name in ("DATE", "Date"):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                pass
        return value

    return value


def migrate():
    """Run the full migration from SQLite to PostgreSQL."""
    if not os.path.isfile(SQLITE_PATH):
        print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)

    print(f"Source: {SQLITE_PATH}")
    print(f"Target: {POSTGRES_URL.split('@')[-1] if '@' in POSTGRES_URL else POSTGRES_URL}")
    print()

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_tables = get_sqlite_tables(sqlite_conn)
    print(f"SQLite tables found: {len(sqlite_tables)}")

    # Connect to PostgreSQL
    pg_engine = create_engine(POSTGRES_URL)

    # Check PostgreSQL has the schema
    pg_inspector = inspect(pg_engine)
    pg_tables = pg_inspector.get_table_names()
    print(f"PostgreSQL tables found: {len(pg_tables)}")

    if not pg_tables or "user" not in pg_tables:
        print("ERROR: PostgreSQL schema not found. Run Alembic migrations first.")
        print("  The app should auto-run migrations on startup.")
        sys.exit(1)

    # Determine migration order
    tables_to_migrate = [t for t in TABLE_ORDER if t in sqlite_tables and t in pg_tables]
    # Add any tables not in TABLE_ORDER
    for t in sqlite_tables:
        if t not in tables_to_migrate and t in pg_tables:
            tables_to_migrate.append(t)

    print(f"Tables to migrate: {len(tables_to_migrate)}")
    print()

    total_rows = 0
    with pg_engine.begin() as pg_conn:
        # Disable FK checks during migration
        pg_conn.execute(text("SET session_replication_role = 'replica'"))

        for table_name in tables_to_migrate:
            rows = get_sqlite_rows(sqlite_conn, table_name)
            if not rows:
                print(f"  {table_name}: 0 rows (skip)")
                continue

            # Get PostgreSQL column types for conversion
            col_types = get_column_info(pg_engine, table_name)

            # Clear existing data in PostgreSQL table
            pg_conn.execute(text(f'DELETE FROM "{table_name}"'))

            # Convert and insert rows
            for row in rows:
                converted = {}
                for key, value in row.items():
                    if key in col_types:
                        converted[key] = convert_value(value, col_types[key])
                    else:
                        converted[key] = value

                columns = ", ".join(f'"{k}"' for k in converted.keys())
                placeholders = ", ".join(f":{k}" for k in converted.keys())
                insert_sql = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})'
                pg_conn.execute(text(insert_sql), converted)

            total_rows += len(rows)
            print(f"  {table_name}: {len(rows)} rows migrated")

        # Re-enable FK checks
        pg_conn.execute(text("SET session_replication_role = 'origin'"))

        # Reset sequences for all tables with integer primary keys
        print()
        print("Resetting PostgreSQL sequences...")
        for table_name in tables_to_migrate:
            try:
                # Find the sequence name for the id column
                result = pg_conn.execute(
                    text(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                ).scalar()
                if result:
                    max_id = pg_conn.execute(
                        text(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"')
                    ).scalar()
                    pg_conn.execute(
                        text(f"SELECT setval('{result}', :max_id, true)"),
                        {"max_id": max(max_id, 1)},
                    )
                    print(f"  {table_name}: sequence reset to {max_id}")
            except Exception as e:
                # Table might not have a sequence (no autoincrement id)
                pass

    sqlite_conn.close()

    # Verify row counts
    print()
    print("Verifying migration...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    mismatches = []
    with pg_engine.connect() as pg_conn:
        for table_name in tables_to_migrate:
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            sqlite_count = sqlite_cursor.fetchone()[0]

            pg_count = pg_conn.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            ).scalar()

            status = "OK" if sqlite_count == pg_count else "MISMATCH"
            if sqlite_count != pg_count:
                mismatches.append(table_name)
            if sqlite_count > 0 or pg_count > 0:
                print(f"  {table_name}: SQLite={sqlite_count} PostgreSQL={pg_count} [{status}]")

    sqlite_conn.close()

    print()
    if mismatches:
        print(f"WARNING: Row count mismatches in: {', '.join(mismatches)}")
        sys.exit(1)
    else:
        print(f"Migration complete. {total_rows} total rows transferred across {len(tables_to_migrate)} tables.")


if __name__ == "__main__":
    migrate()
