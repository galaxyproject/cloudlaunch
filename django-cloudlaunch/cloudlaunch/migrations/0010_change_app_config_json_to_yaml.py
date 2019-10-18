import yaml

from django.db import migrations, models


def save_config_as_yaml(model):
    for obj in model.objects.all():
        config = yaml.safe_load(obj.default_launch_config)
        if config:
            obj.default_launch_config = yaml.dump(
                config, default_flow_style=False)
            obj.save()


def convert_json_app_config_to_yaml(apps, schema_editor):
    AppConfig = apps.get_model('cloudlaunch', 'Application')
    AppVerConfig = apps.get_model('cloudlaunch', 'ApplicationVersion')
    AppVerTargetConfig = apps.get_model(
        'cloudlaunch', 'ApplicationVersionTargetConfig')
    save_config_as_yaml(AppConfig)
    save_config_as_yaml(AppVerConfig)
    save_config_as_yaml(AppVerTargetConfig)


class Migration(migrations.Migration):

    dependencies = [
        ('cloudlaunch', '0009_merge_image_and_cloud_image'),
    ]

    operations = [
        migrations.RunPython(convert_json_app_config_to_yaml)
    ]
