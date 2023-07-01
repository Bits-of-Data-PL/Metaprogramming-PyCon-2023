from weakref import WeakKeyDictionary


class FlyweightMeta(type):
    def __new__(cls, name, bases, attrs):
        attrs['cache'] = WeakKeyDictionary()
        return super(FlyweightMeta, cls).__new__(cls, name, bases, attrs)

    def __call__(cls, *args, **kwargs):
        key = (*args, tuple(kwargs.items()))
        cache = getattr(cls, 'cache')
        return cache.setdefault(key, super(FlyweightMeta, cls).__call__(*args, **kwargs))


class flyweight(object):  # decorator
    def __init__(self, cls):
        self._cls = cls
        self._instances = WeakValueDictionary()

    def __call__(self, *args, **kargs):
        return self._instances.setdefault(
            (args, tuple(kargs.items())),
            self._cls(*args, **kargs))
