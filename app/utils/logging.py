"""Activity logging helper.

Provides ``log_activity`` which creates an :class:`ActivityLog` record for
every significant user or system action.  Entries are retained indefinitely
(minimum 3 years — no auto-deletion).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import g, has_request_context, request

from app.extensions import db
from app.models.log import ActivityLog


def log_activity(
    action: str,
    details: Any | None = None,
    user_id: int | None = None,
    ip_address: str | None = None,
) -> ActivityLog:
    """Record a significant action in the activity log.

    Parameters
    ----------
    action:
        Short action identifier, e.g. ``"login"``, ``"score_change"``.
    details:
        Optional extra information.  If a *dict* or *list* is passed it will
        be serialised to a JSON string before storage.
    user_id:
        The acting user's ID.  Falls back to ``g.current_user.id`` when
        available inside a request context.
    ip_address:
        Client IP.  Falls back to ``request.remote_addr`` when available.
    """
    # Resolve defaults from the request context when not explicitly provided
    if user_id is None and has_request_context():
        current_user = getattr(g, "current_user", None)
        if current_user is not None:
            user_id = current_user.id

    if ip_address is None and has_request_context():
        ip_address = request.remote_addr

    # Serialise complex details to JSON
    if isinstance(details, (dict, list)):
        details = json.dumps(details)

    entry = ActivityLog(
        user_id=user_id,
        action=action,
        details=str(details) if details is not None else None,
        ip_address=ip_address,
        created_at=datetime.utcnow(),
    )
    db.session.add(entry)
    # Flush so the caller can inspect the entry immediately if needed,
    # but leave the final commit to the caller / request teardown.
    db.session.flush()
    return entry
