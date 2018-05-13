"""
Celery settings used during cloudlaunch testing
"""
broker_url = 'memory://'
broker_transport_options = {'polling_interval': .01}
broker_backend = 'memory'
result_backend = 'db+sqlite:///results.db'
result_serializer = 'json'
task_serializer = 'json'
accept_content = ['json']
