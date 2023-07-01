import abc
from weakref import WeakValueDictionary

_singleton_instances = {}


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ParentSingletonMeta(type):
    # _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        parent = cls.__bases__[-1]
        # instances = getattr(parent, '_instances', {})
        # parent._instances = instances

        if parent not in _singleton_instances:
            instance = super().__call__(*args, **kwargs)
            _singleton_instances[parent] = instance
        return _singleton_instances[parent]


class ABCParentSingletonMeta(ParentSingletonMeta, abc.ABCMeta):
    pass
