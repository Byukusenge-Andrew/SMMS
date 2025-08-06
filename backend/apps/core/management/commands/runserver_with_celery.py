import os
import subprocess
import sys
import threading
from django.core.management.base import BaseCommand
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(BaseCommand):
    help = 'Start Django development server with Celery worker and beat'

    def add_arguments(self, parser):
        # Add all runserver arguments
        super().add_arguments(parser)
        parser.add_argument(
            '--no-celery',
            action='store_true',
            help='Skip starting Celery processes',
        )

    def handle(self, *args, **options):
        if not options.get('no_celery'):
            # Start Celery worker in background
            self.start_celery_worker()
            # Start Celery beat in background
            self.start_celery_beat()

        # Start Django runserver
        runserver_command = RunserverCommand()
        runserver_command.run_from_argv([
            'manage.py', 'runserver',
            options.get('addrport', '127.0.0.1:8000')
        ])

    def start_celery_worker(self):
        def run_worker():
            try:
                subprocess.run([
                    sys.executable, '-m', 'celery', 
                    '-A', 'social_media_manager', 
                    'worker', '--loglevel=info'
                ], cwd=os.getcwd())
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to start Celery worker: {e}')
                )

        worker_thread = threading.Thread(target=run_worker, daemon=True)
        worker_thread.start()
        self.stdout.write(
            self.style.SUCCESS('Started Celery worker in background')
        )

    def start_celery_beat(self):
        def run_beat():
            try:
                subprocess.run([
                    sys.executable, '-m', 'celery',
                    '-A', 'social_media_manager',
                    'beat', '--loglevel=info'
                ], cwd=os.getcwd())
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to start Celery beat: {e}')
                )

        beat_thread = threading.Thread(target=run_beat, daemon=True)
        beat_thread.start()
        self.stdout.write(
            self.style.SUCCESS('Started Celery beat in background')
        )