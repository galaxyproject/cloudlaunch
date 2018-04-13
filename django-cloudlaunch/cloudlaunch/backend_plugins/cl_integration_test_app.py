import yaml
from cloudbridge.cloud import CloudProviderFactory
from cloudbridge.cloud.interfaces import TestMockHelperMixin
from rest_framework.serializers import ValidationError
from .cloudman_app import CloudManAppPlugin
from .base_vm_app import BaseVMAppPlugin


class CloudLaunchIntegrationTestApp(BaseVMAppPlugin):
    """
    This app replaces the provider with a mock version if available,
    and is intended to be used exclusively for testing.
    """

    def _get_mock_provider(provider):
        """
        Returns a mock version of a provider if available.
        """
        provider_class = CloudProviderFactory().get_provider_class(
            provider.PROVIDER_ID, get_mock=True)
        return provider_class(provider.config)
    
    def deploy(self, name, task, app_config, provider_config):
        # Replace provider with mock version if available
        provider = self._get_mock_provider(provider_config['cloud_provider'])
        if isinstance(provider, TestMockHelperMixin):
            provider.setUpMock()
        provider_config['cloud_provider'] = provider
        return super(CloudLaunchIntegrationTestApp, self).deploy(
            name, task, app_config, provider_config)
