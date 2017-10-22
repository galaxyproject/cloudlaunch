broker_url = 'redis://localhost:6379/0'
result_backend = 'django-db'
beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
result_serializer = 'json'
task_serializer = 'pickle'
accept_content = ['json', 'pickle']
#accept_content = ['json', 'yaml']
