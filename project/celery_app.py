import os
import sys
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Keep local Celery runs able to resolve imports like apps.orders.tasks.
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_dir = os.path.join(base_dir, 'project')
if project_dir not in sys.path:
    sys.path.append(project_dir)

app = Celery('project')

# Configure Celery using settings.py keys prefixed with 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in tasks.py of installed apps
app.autodiscover_tasks()
