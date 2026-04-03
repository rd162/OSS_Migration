"""Backend blueprint package — re-exports backend_bp for create_app() registration."""
from ttrss.blueprints.backend.views import backend_bp  # noqa: F401
