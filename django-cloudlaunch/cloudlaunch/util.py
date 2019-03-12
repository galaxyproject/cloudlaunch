"""A set of utility functions used by the framework."""
from importlib import import_module


def import_class(name):
    parts = name.rsplit('.', 1)
    cls = getattr(import_module(parts[0]), parts[1])
    return cls
