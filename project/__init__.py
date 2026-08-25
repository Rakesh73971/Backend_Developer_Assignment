# Import the Celery app instance when Django starts.
# Keep the module name distinct from the third-party celery package.
from .celery_app import app as celery_app

__all__ = ('celery_app',)
