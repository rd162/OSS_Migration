"""
Flask-Login session helpers (ADR-0007, R07).
The user_loader callback is registered in ttrss/extensions.py to avoid circular imports.
This module holds any additional session-layer utilities.
AR05: pwd_hash is never placed in the session — only user_id is stored.
"""
