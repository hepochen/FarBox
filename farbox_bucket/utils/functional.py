
# You can't trivially replace this `functools.partial` because this binds to
# classes and returns bound instances, whereas functools.partial (on CPython)
# is a type and its instances don't bind.
def curry(_curried_func, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _curried_func(*(args+moreargs), **dict(kwargs, **morekwargs))
    _curried.__name__ = _curried_func.__name__
    _curried.func_name = _curried_func.func_name
    _curried.original_func = _curried_func
    return _curried



class cached_property(object):
    """
    Decorator that creates converts a method with a single
    self argument into a property cached on the instance.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type):
        res = instance.__dict__[self.func.__name__] = self.func(instance)
        return res

