#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import threading
import subprocess


def start_celery():
    """Start Celery worker and beat in background threads"""
    def run_worker():
        subprocess.run([
            sys.executable, '-m', 'celery',
            '-A', 'social_media_manager',
            'worker', '--loglevel=info'
        ])
    
    def run_beat():
        subprocess.run([
            sys.executable, '-m', 'celery',
            '-A', 'social_media_manager', 
            'beat', '--loglevel=info'
        ])
    
    # Start worker and beat in daemon threads
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    beat_thread = threading.Thread(target=run_beat, daemon=True)
    
    worker_thread.start()
    beat_thread.start()
    
    print("Started Celery worker and beat in background")


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media_manager.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Auto-start Celery when running runserver
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        start_celery()
    
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
