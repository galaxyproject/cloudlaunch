import operator
from importlib import import_module

def getattrd(obj, name):
    """
    Same as ``getattr()``, but allows dot notation lookup.
    """
    try:
        return operator.attrgetter(name)(obj)
    except AttributeError:
        return None

def import_class(name):
    parts = name.rsplit('.', 1)
    cls = getattr(import_module(parts[0]), parts[1])
    return cls