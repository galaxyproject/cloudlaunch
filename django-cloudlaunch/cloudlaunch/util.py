"""A set of utility functions used by the framework."""
from importlib import import_module


def import_class(name):
    parts = name.rsplit('.', 1)
    cls = getattr(import_module(parts[0]), parts[1])
    return cls


def serialize_cloud_config(cloud_config):
    """
    Serialize the supplied model to a dict.

    A subset of the the model fields is returned as used by current
    plugins but more fields can be serialized as needed.

    @type  cloud_config: :class:`.models.ApplicationVersionCloudConfig`
    @param cloud_config: A Django model containing infrastructure
                         specific configuration to be serialized.

    @rtype: ``dict``
    @return: A serialized version of the supplied model.
    """
    return {'id': cloud_config.id,
            'default_instance_type': cloud_config.default_instance_type,
            'default_launch_config': cloud_config.default_launch_config,
            'image_id': cloud_config.image.image_id}
