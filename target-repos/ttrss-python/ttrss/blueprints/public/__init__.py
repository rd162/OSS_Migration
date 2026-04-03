"""Public blueprint package — re-exports public_bp for create_app() registration."""
# Source: ttrss/public.php (entry point) + ttrss/classes/handler/public.php (handler class)
from ttrss.blueprints.public.views import public_bp  # noqa: F401
