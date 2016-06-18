BROKER_URL = 'django://'
#BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"