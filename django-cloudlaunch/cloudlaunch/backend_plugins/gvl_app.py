import yaml
from rest_framework.serializers import ValidationError
from .cloudman_app import CloudManAppPlugin
from .simple_web_app import SimpleWebAppPlugin


class GVLAppPlugin(SimpleWebAppPlugin):

    @staticmethod
    def validate_app_config(provider, name, cloud_config, app_config):
        gvl_config = app_config.get("config_gvl")
        if not gvl_config:
            raise ValidationError("GVL configuration data must be provided.")
        user_data = CloudManAppPlugin().validate_app_config(
            provider, name, cloud_config, gvl_config)
        install_list = []
        install_cmdline = gvl_config.get('gvl_cmdline_utilities', False)
        if install_cmdline:
            install_list.append('gvl_cmdline_utilities')
        install_smrtportal = gvl_config.get('smrt_portal', False)
        if install_smrtportal:
            install_list.append('smrt_portal')
        user_data['gvl_config'] = {'install': install_list}
        user_data['gvl_package_registry_url'] = gvl_config.get('gvl_package_registry_url')
        return user_data

    @staticmethod
    def sanitise_app_config(app_config):
        sanitised_config = super(GVLAppPlugin, GVLAppPlugin).sanitise_app_config(app_config)
        gvl_config = sanitised_config.get("config_gvl")
        sanitised_config['config_gvl'] = CloudManAppPlugin().sanitise_app_config(gvl_config)
        return sanitised_config

    def deploy(self, name, task, app_config, provider_config):
        user_data = provider_config.get('cloud_user_data')
        ud = yaml.safe_dump(user_data, default_flow_style=False,
                            allow_unicode=False)
        provider_config['cloud_user_data'] = ud
        result = super(GVLAppPlugin, self).deploy(
            name, task, app_config, provider_config)
        return result
