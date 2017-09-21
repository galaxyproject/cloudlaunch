"""interface for app plugins."""
import abc


class AppPlugin():
    """Interface class for an application."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractstaticmethod
    def process_app_config(provider, name, cloud_config, app_config):
        """
        Validate and build an internal app config.

        Validate an application config entered by the user and builds a new
        processed dictionary of values which will be used by the launch_app
        method. Raises a ValidationError if the application configuration is
        invalid. This method must execute quickly and should not contain long
        running operations, and is designed to provide quick feedback on
        configuration errors to the client.

        @type  provider: :class:`CloudBridge.CloudProvider`
        @param provider: Cloud provider where the supplied app is to be
                         created.

        @type  name: ``str``
        @param name: Name for this deployment.

        @type  cloud_config: :class:`.cloudlaunch.models.ApplicationVersionCloudConfig`
        @param cloud_config: A Django model containing infrastructure
                             specific configuration for this app.

        @type  app_config: ``dict``
        @param app_config: A dict containing the original, unprocessed version
                           of the app config. The app config is a merged dict
                           of database stored settings and user-entered
                           settings.

        :rtype: ``dict``
        :return: A ``dict` containing the launch configuration.
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
    def launch_app(self, provider, task, name, cloud_config, app_config,
                   user_data):
        """
        Launch a given application on the target infrastructure.

        This operation is designed to be a Celery task, and thus, can contain
        long-running operations.

        @type  provider: :class:`CloudBridge.CloudProvider`
        @param provider: Cloud provider where the supplied deployment is to be
                         created.

        @type  task: :class:`.celery.app.task`
        @param task: Celery Task object, which can be used to report progress.

        @type  name: ``str``
        @param name: Name of this deployment.

        @type  cloud_config: :class:`.cloudlaunch.models.ApplicationVersionCloudConfig`
        @param cloud_config: A Django model containing infrastructure specific
                             configuration for this app.

        @type  app_config: ``dict``
        @param app_config: A dict containing the original, unprocessed version
                           of the app config. The app config is a merged dict
                           of database stored settings and user-entered
                           settings.

        @type  user_data: ``object``
        @param user_data: An object returned by the ``process_app_config()``
                          method which contains a validated and processed
                          version of the ``app_config``.

        :rtype: ``dict``
        :return: Results of the launch process.
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
                 provider, the default return value is ``terminated`` for the
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
