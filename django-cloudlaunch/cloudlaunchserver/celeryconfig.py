broker_url = 'redis://localhost:6379/0'
result_backend = 'django-db'
beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
result_serializer = 'json'
task_serializer = 'json'
accept_content = ['json']
#accept_content = ['json', 'yaml']
