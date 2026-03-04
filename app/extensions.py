"""Flask extensions initialisation."""

from sqlalchemy import event
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialise the database with WAL mode enabled on every SQLite connection."""
    db.init_app(app)

    with app.app_context():

        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
