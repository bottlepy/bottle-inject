import functools

__version__ = "0.1.1"
__all__ = "Plugin Injector inject".split()

import inspect
import sys


py32 = sys.version_info >= (3, 2, 0)


class InjectError(RuntimeError):
    pass


class _InjectionPoint(object):
    """ The object returned by :func:`inject`. """

    def __init__(self, name, parameters=None, config=None):
        self.name = name
        self.parameters = parameters or ()
        self.config = config or {}

    def __eq__(self, other):
        if isinstance(other, _InjectionPoint):
            return self.__dict__ == other.__dict__
        return False

class _ProviderCache(dict):
    """ A self-filling cache for :meth:`Injector.resolve` results. """

    def __init__(self, injector):
        super(_ProviderCache, self).__init__()
        self.injector = injector

    def __missing__(self, func):
        self[func] = value = list(self.injector._resolve(func).items())
        return value


def _unwrap(func):
    if inspect.isclass(func):
        func = func.__init__
    while hasattr(func, '__wrapped__'):
        func = func.__wrapped__
    return func


def _make_null_resolver(name, provider):
    msg = "The dependency provider for %r does not accept configuration (it is not a resolver)." % name
    def null_resolver(*a, **ka):
        if a or ka:
            raise InjectError(msg)
        return provider
    return null_resolver


class Injector(object):
    def __init__(self):
        self.__cache = _ProviderCache(self)
        self._resolvers = {}
        self._never_inject = set('self')

    def add_value(self, name, value, alias=()):
        """ Register a dependency value.

        The dependency value is re-used for every injection and treated as a singleton.

        :param name: Name of the injection point.
        :param value: The singleton to provide.
        :param alias: A list of alternative injection points.
        :return: None
        """
        self.add_provider(name, lambda: value, alias=alias)

    def add_provider(self, name, func, alias=()):
        """ Register a dependency provider.

        A *provider* returns the requested dependency when called. The provider is called with no arguments
        every time the dependency is needed. It is possible to inject other dependencies into the call signature of a
        provider.

        :param name: Name of the injection point.
        :param func: The provider callable.
        :param alias: A list of alternative injection points.
        :return: None
        """
        self.add_resolver(name, _make_null_resolver(name, func), alias=alias)

    def add_resolver(self, name, func, alias=()):
        """ Register a dependency provider resolver.

        A *resolver* returns a cache-able *provider* and may accept injection-point specific configuration. The resolver
        is usually called only once per injection point and the return value is cached. It must return a (callable)
        provider. It is possible to inject other dependencies into the call signature of a resolver.

        :param name: Name of the injection point.
        :param func: The resolver callable.
        :param alias: A list of alternative injection points.
        :return: None
        """
        self._resolvers[name] = func
        for name in alias:
            assert isinstance(name, str)
            self._resolvers[name] = func
        self.__cache.clear()

    def remove(self, name):
        """ Remove any dependency, provider or resolver bound to the named injection point.
        :param name: Name of the injection point to clear.
        :return: None
        """
        if self._resolvers.pop(name):
            self.__cache.clear()

    def provider(self, name, alias=()):
        """ Decorator to register a dependency provider. See :func:`add_provider` for a description.
        :param name: Name of the injection point.
        :param alias: A list of alias names for this injection point.
        :return: Decorator that registers the provider function to the injector.
        """
        assert isinstance(name, str)

        def decorator(func):
            self.add_provider(name, func, alias=alias)
            return func

        return decorator

    def resolver(self, name, alias=()):
        """ Decorator to register a dependency provider resolver. See :func:`add_resolver` for a description.
        :param name: Name of the injection point.
        :param alias: A list of alias names for this injection point.
        :return: Decorator that registers the resolver to the injector.
        """
        assert isinstance(name, str)

        def decorator(func):
            self.add_resolver(name, func, alias=alias)
            return func

        return decorator

    def inspect(self, func):
        """ Return a dict that maps parameter names to injection points for the provided callable. """
        func = _unwrap(func)

        if py32:
            args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(func)
        else:
            args, varargs, keywords, defaults = inspect.getargspec(func)
            kwonlyargs, kwonlydefaults, annotations = [], {}, {}

        defaults = defaults or ()

        injection_points = {}

        for arg in args[:len(args) - len(defaults or [])]:
            if arg not in self._never_inject:
                injection_points[arg] = _InjectionPoint(arg)

        for arg, value in zip(args[::-1], defaults[::-1]):
            if isinstance(value, _InjectionPoint):
                injection_points[arg] = value

        for arg, value in kwonlydefaults.items():
            if isinstance(value, _InjectionPoint):
                injection_points[arg] = value

        for arg, value in annotations.items():
            if isinstance(value, _InjectionPoint):
                injection_points[arg] = value

        return injection_points

    def _resolve(self, func):
        """ Given a callable, return a dict that maps argument names to provider callables. The providers are
            resolved and wrapped already and should be called with no arguments to receive the injectable.

            This is called by __ProviderCache.__missing__ and should not be used in other situations.
        """
        results = {}
        for arg, ip in self.inspect(func).items():
            results[arg] = self._prime(ip.name, ip.parameters, ip.config)
        return results

    def _prime(self, name, parameters=None, config=None):
        """ Prepare a named resolver with the specified parameters and configuration.

            Internal use only. See _resolve()
        """
        try:
            provider_resolver = self._resolvers[name]
        except KeyError:
            raise InjectError("Could not resolve provider for injection point %r" % name)

        provider = self.call_inject(provider_resolver, *parameters, **config)
        return self.wrap(provider)

    def call_inject(self, func, *a, **ka):
        """ Call a function and inject missing dependencies. If you want to call the same function multiple times,
            consider :method:`wrap`ing it.
        """
        for key, producer in self.__cache[func]:
            if key not in ka:
                ka[key] = producer()
        return func(*a, **ka)

    def wrap(self, func):
        """ Turn a function into a dependency managed callable.

        Usage::
            @injector.wrap
            def my_func(db: inject('database')):
                pass

        or::
            managed_callable = injector.wrap(my_callable)

        :param func: A callable with at least one injectable parameter.
        :return: A wrapped function that calls :method:`call_inject` internally.

        If the provided function does not accept any injectable parameters, it is returned unchanged.
        """
        cache = self.__cache  # Avoid dot lookup in hot path

        # Skip wrapping for functions with no injection points
        if not self.inspect(func):
            return func

        @functools.wraps(func)
        def wrapper(*a, **ka):
            # PERF: Inlined call_inject call. Keep in sync with the implementation above.
            for key, producer in cache[func]:
                if key not in ka:
                    ka[key] = producer()
            return func(*a, **ka)

        wrapper.__injector__ = self
        return wrapper


class Plugin(Injector):
    api = 2

    def __init__(self):
        super(Plugin, self).__init__()
        self.app = None

    def setup(self, app):
        from bottle import request, response

        self.app = app
        self.add_value('injector', self)
        self.add_value('config', app.config)
        self.add_value('app', app)
        self.add_value('request', request, alias=['req', 'rq'])
        self.add_value('response', response, alias=['res', 'rs'])

    def apply(self, callback, route):
        if self.inspect(callback):
            return self.wrap(callback)
        return callback


def inject(name, *args, **kwargs):
    """ Mark an argument in a function signature as an injection point.

        The return value can be used as an annotation (Python 3) or default value (Python 2) for parameters that should
        be replaced by dependency injection.

    Usage::
        def my_func(a: inject('name'),
                    b: inject('name', 'opt', conf="val") # Resolvers only.
            ):
            pass

    :param name: Name of the dependency to inject.
    :param args: Additional arguments passed to the dependency provider resolver.
    :param kwargs: Additional keyword arguments passed to the dependency provider resolver.
    :return:
    """
    return _InjectionPoint(name, args, kwargs)

