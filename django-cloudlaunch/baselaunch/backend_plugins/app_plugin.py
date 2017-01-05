"""Base interfaces for app plugins."""
import abc


class BaseAppPlugin():
    """Interface class for an application."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractstaticmethod
    def process_app_config(self, name, cloud_version_config, credentials,
                           app_config):
        """
        Validate and build an internal app config.

        Validate an application config entered by the user and builds a new
        processed dictionary of values which will be used by the launch_app
        method. Raises a ValidationError if the application configuration is
        invalid. This method must execute quickly and should not contain long
        running operations, and is designed to provide quick feedback on
        configuration errors to the client.

        :rtype: ``dict``
        :return: a ``dict` containing the launch configuration
        """
        pass

    @abc.abstractmethod
    def launch_app(self, task, name, version_config, credentials, app_config,
                   user_data):
        """Launch a given application on the target infrastructure."""
        pass
