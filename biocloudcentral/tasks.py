import time
from celery import task


@task()
def add(x, y):
    time.sleep(5)
    return x + y
