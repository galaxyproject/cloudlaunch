from collections import OrderedDict
import yaml

from rest_framework import serializers

from cloudlaunch import models as cl_models


class StoredYAMLField(serializers.JSONField):
    def __init__(self, *args, **kwargs):
        super(StoredYAMLField, self).__init__(*args, **kwargs)

    def to_internal_value(self, data):
        try:
            if data:
                return yaml.safe_dump(data, default_flow_style=False,
                                      allow_unicode=True)
            else:
                return None
        except (TypeError, ValueError):
            self.fail('invalid')
        return data

    def to_representation(self, value):
        try:
            if value:
                return yaml.safe_load(value)
            else:
                return value
        except Exception:
            return value


class AppVersionSerializer(serializers.ModelSerializer):
    default_launch_config = StoredYAMLField(required=False, allow_null=True)

    def get_unique_together_validators(self):
        """Overriding method to disable unique together checks"""
        return []

    class Meta:
        model = cl_models.ApplicationVersion
        fields = ('version', 'frontend_component_path', 'frontend_component_name',
                  'backend_component_name', 'default_launch_config')


class ApplicationSerializer(serializers.ModelSerializer):
    default_launch_config = StoredYAMLField(required=False, allow_null=True,
                                            validators=[])
    default_version = serializers.CharField(source='default_version.version', default=None,
                                            allow_null=True, required=False)
    versions = AppVersionSerializer(many=True)

    def create(self, validated_data):
        return self.update(None, validated_data)

    def update(self, instance, validated_data):
        slug = validated_data.pop('slug')
        versions = validated_data.pop('versions')
        default_version = validated_data.pop('default_version')

        # create the app
        app, _ = cl_models.Application.objects.update_or_create(
            slug=slug, defaults=validated_data)

        # create all nested app versions
        for version in versions:
            ver_id = version.pop('version')
            cl_models.ApplicationVersion.objects.update_or_create(
                application=app, version=ver_id, defaults=version)

        # Now set the default app version
        if default_version and default_version['version']:
            app.default_version = cl_models.ApplicationVersion.objects.get(
                application=app, version=default_version['version'])
            app.save()

        return app

    class Meta:
        model = cl_models.Application
        fields = ('slug', 'name', 'status', 'summary', 'maintainer',
                  'description', 'info_url', 'icon_url', 'display_order',
                  'default_version', 'default_launch_config', 'versions')
        extra_kwargs = {
            'slug': {'validators': []}
        }


# Control YAML serialization

# xref: https://github.com/wimglenn/oyaml/blob/de97b8b2be072a8072e807182ffe3fa11c504fd7/oyaml.py#L10
def map_representer(dumper, data):
    return dumper.represent_dict(data.items())


def yaml_literal_representer(dumper, data):
    if len(data) > 50:
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    else:
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data)


yaml.add_representer(str, yaml_literal_representer)
yaml.add_representer(str, yaml_literal_representer, Dumper=yaml.dumper.SafeDumper)
yaml.add_representer(OrderedDict, map_representer)
yaml.add_representer(OrderedDict, map_representer, Dumper=yaml.dumper.SafeDumper)
