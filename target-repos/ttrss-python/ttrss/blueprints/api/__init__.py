"""API blueprint package — re-exports api_bp for create_app() registration."""
from ttrss.blueprints.api.views import api_bp  # noqa: F401
