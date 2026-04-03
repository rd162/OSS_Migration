"""API blueprint package — re-exports api_bp for create_app() registration."""
# Source: ttrss/api/index.php (entry point) + ttrss/classes/api.php (handler class)
from ttrss.blueprints.api.views import api_bp  # noqa: F401
