"""interface for app plugins."""
import abc


class AppPlugin():
    """Interface class for an application."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractstaticmethod
    def process_app_config(name, cloud_version_config, credentials,
                           app_config):
        """
        Validate and build an internal app config.

        Validate an application config entered by the user and builds a new
        processed dictionary of values which will be used by the launch_app
        method. Raises a ValidationError if the application configuration is
        invalid. This method must execute quickly and should not contain long
        running operations, and is designed to provide quick feedback on
        configuration errors to the client.

        @type  name: ``str``
        @param name: Name of this deployment
        
        @type  version_config: :class:`.cloudlaunch.models.ApplicationVersionCloudConfig`
        @param version_config: A django model containing infrastructure specific
               configuration for this app.
        
        @type  credentials: ``dict``
        @param credentials: A dict containing provider specific credentials.
                
        @type  app_config: ``dict``
        @param app_config: A dict containing the original, unprocessed version
               of the app config. The app config is a merged dict of database
               stored settings and user-entered settings.

        :rtype: ``dict``
        :return: a ``dict` containing the launch configuration
        """
        pass

    @abc.abstractstaticmethod
    def sanitise_app_config(app_config):
        """
        Sanitises values in the app_config and returns it.

        The returned representation should have all sensitive data such
        as passwords and keys removed, so that it can be safely logged.

        @type  app_config: ``dict``
        @param app_config: A dict containing the original, unprocessed version
               of the app config. The app config is a merged dict of database
               stored settings and user-entered settings.

        :rtype: ``dict``
        :return: a ``dict` containing the launch configuration
        """
        pass

    @abc.abstractmethod
    def launch_app(self, task, name, version_config, credentials, app_config,
                   user_data):
        """
        Launch a given application on the target infrastructure. This operation
        is designed to be a celery task, and thus, can contain long-running
        operations.
        
        @type  task: :class:`.celery.app.task`
        @param task: celery Task object, which can be used to report progress
        
        @type  name: ``str``
        @param name: Name of this deployment
        
        @type  version_config: :class:`.cloudlaunch.models.ApplicationVersionCloudConfig`
        @param version_config: A django model containing infrastructure specific
               configuration for this app.
        
        @type  credentials: ``dict``
        @param credentials: A dict containing provider specific credentials.
                
        @type  app_config: ``dict``
        @param app_config: A dict containing the original, unprocessed version
               of the app config. The app config is a merged dict of database
               stored settings and user-entered settings.
                           
        @type  user_data: ``object``
        @param user_data: An object returned by the process_app_config() method which
               contains a validated and processed version of the app_config.

        :rtype: ``dict``
        :return: a ``dict` containing the results of the launch.
        """
        pass

    @abc.abstractmethod
    def check_status(self, deployment, credentials):
        """
        Check the status of this app.

        At a minimum, this will check the status of the VM on which the
        deployment is running. Applications can implement more elaborate
        status checks.

        @type  deployment: ``ApplicationDeployment``
        @param deployment: An instance of the app deployment on which status
                           to check.

        @type  credentials: ``dict``
        @param credentials: Cloud provider credentials to use when checking
                            the status.

        :rtype: ``dict``
        :return: A dictionary with possibly app-specific fields capturing
                 app status. At a minimum, ``instance_status`` field will be
                 available.
        """
        pass

    @abc.abstractmethod
    def delete(self, deployment, credentials):
        """
        Delete resource(s) associated with the supplied deployment.

        *Note* that this method will delete resource(s) associated with
        the deployment - this is un-recoverable action.

        @type  deployment: ``ApplicationDeployment``
        @param deployment: An instance of the app deployment to delete.

        @type  credentials: ``dict``
        @param credentials: Cloud provider credentials to use when deleting
                            the deployment.

        :rtype: ``bool``
        :return: The result of delete invocation.
        """
        pass
