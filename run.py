"""Entry point for the Tōtika Audit Web Application."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    # Use stat reloader for reliable hot reload inside Docker on Windows
    use_reloader = debug
    reloader_type = "stat" if os.environ.get("FLASK_RUN_IN_DOCKER") else None
    app.run(
        debug=debug,
        host="0.0.0.0",
        port=5000,
        use_reloader=use_reloader,
        reloader_type=reloader_type,
    )
