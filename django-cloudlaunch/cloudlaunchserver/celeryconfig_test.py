"""
Celery settings used during cloudlaunch testing
"""
broker_backend = 'memory'
task_always_eager = True
eager_propagates_exceptions = True
result_serializer = 'json'
task_serializer = 'json'
accept_content = ['json']
