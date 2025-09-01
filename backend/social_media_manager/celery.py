import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media_manager.settings")

app = Celery("social_media_manager")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Configure periodic tasks
app.conf.beat_schedule = {
    'check-expired-trials': {
        'task': 'apps.authentication.tasks.check_expired_trials',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
    'send-trial-reminders': {
        'task': 'apps.authentication.tasks.send_trial_reminders',
        'schedule': crontab(hour=10, minute=0),  # Run daily at 10 AM
    },
}

app.conf.timezone = 'UTC'

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
