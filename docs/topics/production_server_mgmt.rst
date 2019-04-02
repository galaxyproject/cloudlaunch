Notes on managing the production server
=======================================

Upgrading running chart
-----------------------

1. Fetch latest chart version through
:code:`helm repo update`


2. Docker pull the latest image

.. code-block:: bash

    sudo docker pull cloudve/cloudlaunch-server:latest
    sudo docker pull cloudve/cloudlaunch-ui:latest`


3. Upgrade then helm chart

.. code-block:: bash

    helm upgrade --reuse-values <chart_name> galaxyproject/cloudlaunch


Reinstalling chart from scratch
-------------------------------

0. Note down the existing secrets for fernet keys, secret keys, db password etc. through kubernetes in the cloudlaunch namespace.
Dashboard access link: https://149.165.157.211:4430/k8s/clusters/c-nmrvs/api/v1/namespaces/kube-system/services/https:kubernetes-dashboard:/proxy/#!/login

To obtain login token: https://gist.github.com/superseb/3a9c0d2e4a60afa3689badb1297e2a44

.. code-block:: bash

    kubectl -n kube-system describe secret $(kubectl -n kube-system get secret | grep admin-user | awk '{print $1}')

1. :code:`helm delete <existing_chart>`

2. :code:`kubectl delete namespace cloudlaunch`

3. Optionally, delete all cached docker images using

.. code-block:: bash

    docker images
    docker rmi

4. Delete existing persistent volume in rancher. This does not delete the local folder, so the database will survive. Recreate with following settings:

.. code-block:: bash

    Name: cloudlaunch-database
    Capacity: 30
    Volume Plugin: Local Node Path
    Path on the node: /opt/cloudlaunch/database
    Path on node: A directory, or create
    Customize -> Many nodes read write


5. :code:`helm install galaxyproject/cloudlaunch --set cloudlaunch-server.postgresql.postgresqlPassword=<pg_password> --namespace cloudlaunch --set cloudlaunch-server.fernet_keys[0]='<replace with fernet key 1>' --set cloudlaunch-server.fernet_keys[1]='<replace with fernet key 2>' --set cloudlaunch-server.secret_key=<replace with secret key>`


