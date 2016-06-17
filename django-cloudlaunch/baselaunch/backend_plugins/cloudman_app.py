from rest_framework.serializers import ValidationError

class CloudManConfigHandler():
    
    def get_required_val(self, data, name, message):
        val = data.get(name)
        if not val:
            raise ValidationError(message)
        return val
   
    def process_config_data(self, data):
        print(data)
        cloudman_config = self.get_required_val(data, "config_cloudman",
                                                "CloudMan configuration data must be provided.")
        user_data = {}
        user_data['bucket_default'] = self.get_required_val(cloudman_config, "defaultBucket",
                                                            "default bucket is required.")
        user_data['cluster_name'] = self.get_required_val(cloudman_config, "clusterName",
                                                          "cluster name is required.")
        user_data['password'] = self.get_required_val(cloudman_config, "clusterPassword",
                                                      "cluster name is required.")
        user_data['initial_cluster_type'] = self.get_required_val(cloudman_config, "clusterType",
                                                                  "cluster type is required.")
        user_data['storageType'] = self.get_required_val(cloudman_config, "storageType",
                                                         "storage type is required.")
        user_data['storage_size'] = cloudman_config.get("storageSize")
        user_data['post_start_script_url'] = cloudman_config.get("masterPostStartScript")
        user_data['worker_post_start_script_url'] = cloudman_config.get("workerPostStartScript")
        user_data['share_string'] = cloudman_config.get("clusterSharedString")
        user_data['cluster_templates'] = cloudman_config.get("cluster_templates")
        return user_data;
    