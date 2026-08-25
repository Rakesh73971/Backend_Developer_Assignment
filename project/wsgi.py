import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Append project/ directory to the end of sys.path to enable apps.* imports
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_dir = os.path.join(base_dir, 'project')
if project_dir not in sys.path:
    sys.path.append(project_dir)

application = get_wsgi_application()
