#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    # Set the settings module to project.settings since manage.py is at the root
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    
    # Add the project/ directory to the end of sys.path.
    # This allows resolving imports like "apps.products" while preventing
    # local "celery.py" from shadowing the third-party "celery" library.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(base_dir, 'project')
    if project_dir not in sys.path:
        sys.path.append(project_dir)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
