"""interface for app plugins."""
import abc


class AppPlugin():
    """Interface class for an application."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractstaticmethod
    def validate_app_config(provider, name, cloud_config, app_config):
        """
        Validate and build an internal app config.

        Validate an application config entered by the user and builds a new
        processed dictionary of values which will be used by the ``deploy``
        method. Raises a ``ValidationError`` if the application configuration
        is invalid. This method must execute quickly and should not contain
        long running operations, and is designed to provide quick feedback on
        configuration errors to the client.

        @type  provider: :class:`CloudBridge.CloudProvider`
        @param provider: Cloud provider where the supplied app is to be
                         created.

        @type  name: ``str``
        @param name: Name for this deployment.

        @type  cloud_config: ``dict``
        @param cloud_config: A dict containing cloud infrastructure specific
                             configuration for this app.

        @type  app_config: ``dict``
        @param app_config: A dict containing the original, unprocessed version
                           of the app config. The app config is a merged dict
                           of database stored settings and user-entered
                           settings.

        :rtype: ``dict``
        :return: A validated ``dict` containing the app launch configuration.
        """
        pass

    @abc.abstractstaticmethod
    def sanitise_app_config(app_config):
        """
        Sanitise values in the app_config.

        The returned representation should have all sensitive data such
        as passwords and keys removed, so that it can be safely logged.

        @type  app_config: ``dict``
        @param app_config: A dict containing the original, unprocessed version
                           of the app config. The app config is a merged dict
                           of database stored settings and user-entered
                           settings.

        :rtype: ``dict``
        :return: A ``dict` containing the launch configuration.
        """
        pass

    @abc.abstractmethod
    def deploy(self, name, task, app_config, provider_config):
        """
        Deploy this app plugin on the supplied provider.

        Perform all the necessary steps to deploy this appliance. This may
        involve provisioning cloud resources or configuring existing host(s).
        See the definition of each method argument as some have required
        structure.

        This operation is designed to be a Celery task, and thus, can contain
        long-running operations.

        @type  name: ``str``
        @param name: Name of this deployment.

        @type  task: :class:`Task`
        @param task: A Task object, which can be used to report progress. See
                     ``tasks.Task`` for the interface details and sample
                     implementation.

        @type  app_config: ``dict``
        @param app_config: A dict containing the appliance configuration. The
                           app config is a merged dict of database stored
                           settings and user-entered settings. In addition to
                           the static configuration of the app, such as
                           firewall rules or access password, this should
                           contain a url to a host configuration playbook, if
                           such configuration step is desired. For example:
                           ```
{
   "config_cloudman": {},
   "config_appliance": {
      "sshUser": "ubuntu",
      "runner": "ansible",
      "repository": "https://github.com/afgane/Rancher-Ansible",
      "inventoryTemplate": "https://gist.githubusercontent.com/..."
   },
   "config_cloudlaunch": {
       "vmType": "c3.large",
       "firewall": [ {
             "securityGroup": "cloudlaunch-cm2",
             "rules": [ {
                   "protocol": "tcp",
                   "from": "22",
                   "to": "22",
                   "cidr": "0.0.0.0/0"
                } ] } ] } }
```
        @type  provider_config: ``dict``
        @param provider_config: Define the details of of the infrastructure
                                provider where the appliance should be
                                deployed. It is expected that this dictionary
                                is composed within a task calling the plugin so
                                it reflects the supplied info and derived
                                properties. See ``tasks.py → create_appliance``
                                for an example.
                                The following keys are supported:
                                * ``cloud_provider``: CloudBridge object of the
                                                      cloud provider
                                * ``cloud_config``: A dict containing cloud
                                                    infrastructure specific
                                                    configuration for this app
                                * ``cloud_user_data``: An object returned by
                                                       ``validate_app_config()``
                                                       method which contains a
                                                       validated and formatted
                                                       version of the
                                                       ``app_config`` to be
                                                       supplied as instance
                                                       user data
                                * ``host_address``: A host IP address or a
                                                    hostnames where to deploy
                                                    this appliance
                                * ``ssh_user``: User name with which to access
                                                the host(s)
                                * ``ssh_public_key``: Public RSA ssh key to be
                                                      used when running the app
                                                      configuration step. This
                                                      should be the actual key.
                                                      CloudLaunch will auto-gen
                                                      this key for provisioned
                                                      instances. For hosted
                                                      instances, the user
                                                      should retrieve
                                                      CloudLaunch's public key
                                                      but this value should not
                                                      be supplied.
                                * ``ssh_private_key``: Private portion of an
                                                       RSA ssh key. This should
                                                       not be supplied by a
                                                       user and is intended
                                                       only for internal use.

        :rtype: ``dict``
        :return: Results of the deployment process.
        """
        pass

    @abc.abstractmethod
    def health_check(self, provider, deployment):
        """
        Check the health of this app.

        At a minimum, this will check the status of the VM on which the
        deployment is running. Applications can implement more elaborate
        health checks.

        @type  provider: :class:`CloudBridge.CloudProvider`
        @param provider: Cloud provider where the supplied deployment was
                         created.

        @type  deployment: ``dict``
        @param deployment: A dictionary describing an instance of the
                           app deployment. The dict must have at least
                           `launch_result` and `launch_status` keys.

        :rtype: ``dict``
        :return: A dictionary with possibly app-specific fields capturing
                 app health. At a minimum, ``instance_status`` field will be
                 available. If the deployment instance is not found by the
                 provider, the default return value is ``deleted`` for the
                 ``instance_status`` key.
        """
        pass

    @abc.abstractmethod
    def restart(self, provider, deployment):
        """
        Restart the appliance associated with the supplied deployment.

        This can simply restart the virtual machine on which the deployment
        is running or issue an app-specific call to perform the restart.

        @type  provider: :class:`CloudBridge.CloudProvider`
        @param provider: Cloud provider where the supplied deployment was
                         created.

        @type  deployment: ``dict``
        @param deployment: A dictionary describing an instance of the
                           app deployment to be restarted. The dict must have
                           at least `launch_result` and `launch_status` keys.

        :rtype: ``bool``
        :return: The result of restart invocation.
        """
        pass

    @abc.abstractmethod
    def delete(self, provider, deployment):
        """
        Delete resource(s) associated with the supplied deployment.

        *Note* that this method will delete resource(s) associated with
        the deployment - this is an un-recoverable action.

        @type  provider: :class:`CloudBridge.CloudProvider`
        @param provider: Cloud provider where the supplied deployment was
                         created.

        @type  deployment: ``dict``
        @param deployment: A dictionary describing an instance of the
                           app deployment to be deleted. The dict must have at
                           least `launch_result` and `launch_status` keys.

        :rtype: ``bool``
        :return: The result of delete invocation.
        """
        pass
