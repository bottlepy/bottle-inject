Bottle Dependency Injection
===========================

The Bottle framework already does dependency injection in some regard: The URL parameters of your routes are injected into your handler functions as keyword arguments. Some other Plugins (actually, most plugins) do it, too: They inject database connections, authentication contexts, session objects and much more. This Plugin makes the concept available to you without the need to write a new plugin for every single dependency you want to inject. It also can change the way you use Bottle and write applications in a funcamental way, if you let it. If done right, dependency injection can reduce the complexity and increase testability and readability of your application a lot. But let us start easy, with a simple example::

    app = Bottle()
    injector = app.install('bottle.ext.inject:Plugin')

    @injector.provider('db')
    def get_db_handle():
        return my_database_connection.cursor()

    @app.route('/random_quote')
    def random_quote(db):
        row = db.execute('SELECT quote FROM quotes ORDER BY RANDOM() LIMIT 1').fetchone()
        return row['quote']

The first two lines are nothing new. We just create a bottle application and install this plugin to it. The next block is more interesting. Similar to how bottle binds handler functions to URL paths, the injector binds providers to injection points. In this case, we bind the provider 'get_db_handle' to the injection point named 'db'. Whenver a function is called through our injector and has an argument with the same name, it recieves a fresh database cursor from our provider. You can see that in the next few lines. Because all handler callbacks are managed by our injector plugin, you just need to accept a 'db' argument and it is automatically injected for us by the plugin. If you define a route that does not accept a 'db' argument, then nothing happens. No database curser is ever created for that route.

That little example shows the benefits of dependency injection very well:

  * You can unit-test the 'random_quote()' function directly by passing it a fake- or test-database object. No need to set-up the whole application just for testing.
  * No global variables or global state used. The function can be used again in a different context without hassle.
  * You don't have to import `get_db_handle` into every module that defines bottle application routes.
  * You can change the implementation of 'get_db_handle' and it affects every route of your application. No need to search/replace your codebase.
  * Less typing. Be lazy where it counts.

Advanced usage
==============

Values, Providers and Resolvers
-------------------------------

The dependency value is re-used for every injection and treated as a singleton.

A *provider* returns the requested dependency when called. The provider is called with no arguments every time the dependency is needed.

A *resolver* returns a cache-able *provider* and may accept injection-point specific configuration. The resolver is usually called only once per injection point and the return value is cached. It must return a (callable) provider.

Injection Points
----------------

TODO: Describe the inject() function and how it is used.

::

    def my_func(
        db                 # Positional arguments are always recognized as an injection point with the same name.
        a = 'value'        # Keyword arguments with default values are not recognized.
        b = inject('db')   # Here we explicitly define an injection point. The name of the argument is no longer
                           #  important.
        c: inject('db')    # In Python 3 you can use the annotation syntax. (recommended)
    ):
        pass

::

    # Python 2
    def func(name = inject('param', 'name'),
             file = inject('file', 'upload')):
        pass

    # Python 3
    def func(name: inject('param', 'name'),
             file: inject('file', 'upload')):
        pass

TODO: You can disable the injection into unannotized arguments (maybe).

Recursive Dependency Injection
------------------------------
TODO: Describe recursive injection (injecting stuff into providers and resolvers).

Default injection points
------------------------

The plugin comes with a set pre-defined providers. You can use them right away, or unregister them if you don't want them.

=================  =========================  =====  ===============================================
Injection Points   Type                       Scope  Description
=================  =========================  =====  ===============================================
request, req, rq   `bottle.Request`           local
response, res, rs  `bottle.Request`           local
injector           `Injector`                 app    The injector itself. Can be used for runtime
                                                     inspection if injectable values, e.g. by other
                                                     plugins.
params             `bottle.FormsDict`         local  Not implenented.
param[name]        `str`                      local  Not implenented.
=================  =========================  =====  ===============================================

What is "Dependency Injection"?
===============================

The term "Dependency Injection" is just a fancy name for a simple concept: The *caller* of a piece of code should *provide* all *depnendencies* the code needs to run. In other words: A function or object should not need to *reach out*, but be *provided* with everything it needs.

A small example probably helps best. The following code does *not* follow dependency injection paradigm::

    db = my_database_connection.cursor()

    def do_stuff():
        db.execute('...')

    do_stuff()

And now, with dependency injection::

    def do_stuff(db):
        db.execute('...')

    do_stuff(my_database_connection.cursor())

The only difference is that we now pass the database connction handle to the function explicitly, instead of letting the function fetch it from the global namespace. That's basically it. Now you can easily test `do_stuff` by passing it a fake database connection or a connection to a test database, re-use it in other contexts with different darabases, and the possible side-effects are no longer hidden within the code.

On the downside, you'd have to type more and pass around a lot of stuff, but that is exactly what this plugin does for you: It manages the dependencies and injects them where needed.

Glossary
--------

Injector
    An object that manages *Dependencies*, *Providers* and *Resolvers* and can be asked to inject the required
    dependencies into a function call.

Injection Point
    A place to inject dependencies into. This plugin injects into function call arguments most of the time.

Consumer
    A function or callable that defines dependencies in its call signature so that the injector can inject them.

Dependency
    An object or resource that can be injected.

Provider
    A function or callable that creates dependencies on demand, or otherwise provides the dependencies for when they are needed.

Resolver
    A function or callable that creates individual providers based on injection-point specific configuration. (Yes, you could call it a dependency-provoder-provider but that sounds aweful)
