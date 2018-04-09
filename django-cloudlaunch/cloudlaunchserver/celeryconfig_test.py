"""
Celery settings used during cloudlaunch testing
"""
broker_backend = 'memory'
always_eager = True
eaer_propagates_exceptions = True
result_serializer = 'json'
task_serializer = 'json'
accept_content = ['json']
