import yaml
from rest_framework.serializers import ValidationError
from .cloudman_app import CloudManAppPlugin
from .simple_web_app import SimpleWebAppPlugin


class GVLAppPlugin(SimpleWebAppPlugin):

    @staticmethod
    def process_app_config(provider, name, cloud_config, app_config):
        gvl_config = app_config.get("config_gvl")
        if not gvl_config:
            raise ValidationError("GVL configuration data must be provided.")
        user_data = CloudManAppPlugin().process_app_config(
            provider, name, cloud_config, gvl_config)
        install_list = []
        install_cmdline = gvl_config.get('gvl_cmdline_utilities', False)
        if install_cmdline:
            install_list.append('gvl_cmdline_utilities')
        install_smrtportal = gvl_config.get('smrt_portal', False)
        if install_smrtportal:
            install_list.append('smrt_portal')
        user_data['gvl_config'] = {'install': install_list}
        return user_data

    @staticmethod
    def sanitise_app_config(app_config):
        sanitised_config = super(GVLAppPlugin, GVLAppPlugin).sanitise_app_config(app_config)
        gvl_config = sanitised_config.get("config_gvl")
        sanitised_config['config_gvl'] = CloudManAppPlugin().sanitise_app_config(gvl_config)
        return sanitised_config

    def launch_app(self, provider, task, name, cloud_config,
                   app_config, user_data):
        ud = yaml.dump(user_data, default_flow_style=False, allow_unicode=False)
        result = super(GVLAppPlugin, self).launch_app(
            provider, task, name, cloud_config, app_config, ud)
        return result
