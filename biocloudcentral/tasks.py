# import time
from celery import task
from bioblend.cloudman.launch import CloudManLauncher


@task()
def add(x, y):
    """
    A task used during testing; adds two provided numbers
    """
    # time.sleep(5)
    # print "in add"
    return x + y


@task()
def fetch_clusters(cloud, a_key, s_key):
    """
    Given a cloud object and appropriate credentials, retrieve a list of
    clusters associated with the given account. Return a dict of clusters'
    persistent data.
    """
    cml = CloudManLauncher(a_key, s_key, cloud)
    return cml.get_clusters_pd()
