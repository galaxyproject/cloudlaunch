from rest_framework.serializers import ValidationError
from .cloudman_app import CloudManConfigHandler

class GVLConfigHandler():
    
    def process_config_data(self, cloud_version_config, data):
        gvl_config = data.get("config_gvl")
        if not gvl_config:
            raise ValidationError("GVL configuration data must be provided.")
        user_data = CloudManConfigHandler().process_config_data(cloud_version_config, gvl_config)
        install_list = []
        install_cmdline = gvl_config.get('gvl_cmdline_utilities', False)
        if install_cmdline:
            install_list.append('gvl_cmdline_utilities')
        install_smrtportal = gvl_config.get('smrt_portal', False)
        if install_smrtportal:
            install_list.append('smrt_portal')
        user_data['gvl_config'] = { 'install' : install_list }
        return user_data;
    