"""Public blueprint package — re-exports public_bp for create_app() registration."""
from ttrss.blueprints.public.views import public_bp  # noqa: F401
