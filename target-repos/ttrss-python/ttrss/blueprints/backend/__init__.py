"""Backend blueprint package — re-exports backend_bp for create_app() registration."""
# Source: ttrss/backend.php (entry point) + ttrss/classes/backend.php (dispatch class)
from ttrss.blueprints.backend.views import backend_bp  # noqa: F401
