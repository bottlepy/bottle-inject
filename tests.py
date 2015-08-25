from collections import Counter
from bottle_inject import inject, Injector, InjectError, Plugin
import unittest
import functools

def as_implicit(ip):
    ip.implicit = True
    return ip

class TestInjector(unittest.TestCase):

    def setUp(self):
        self.seq = range(10)

    def test_inject_compare(self):
        self.assertEqual(inject('x'), inject('x'))
        self.assertEqual(inject('x', bar=6, foo=5), inject('x', foo=5, bar=6))
        self.assertNotEqual(inject('x', foo=5), inject('x'))
        self.assertNotEqual(inject('y'), inject('x'))
        self.assertNotEqual(inject('x'), inject('x'))
        self.assertNotEqual(inject('x'), 'x')

    def _common_checks(self, results):
        self.assertEqual(as_implicit(inject('a')), results['a'])
        self.assertEqual(as_implicit(inject('_b')), results['_b'])
        self.assertEqual(None, results.get('c'))
        self.assertEqual(inject('x'), results['d'])
        self.assertFalse(results['d'].implicit)
        self.assertEqual(inject('x2', foo='foo', bar="baz"), results['e'])
        self.assertFalse(results['e'].implicit)
        self.assertEqual(None, results.get('f'))
        self.assertEqual(None, results.get('g'))

    def test_inspection(self):
        def test(a, _b, c=5, d=inject('x'), e=inject('x2', foo='foo', bar="baz"), *f, **g): pass
        self._common_checks(Injector().inspect(test))

    def test_inspect_class(self):
        class Foo:
            def __init__(self, a, _b, c=5, d=inject('x'), e=inject('x2', foo='foo', bar="baz"), *f, **g):
                pass
        self._common_checks(Injector().inspect(Foo))

    def test_inspect_blacklist(self):
        def test(self, a): pass
        self.assertEquals(['a'], Injector().inspect(test).keys())

    def test_inspect_wrapped(self):
        def test(a, _b, c=5, d=inject('x'), e=inject('x2', foo='foo', bar="baz"), *f, **g): pass
        @functools.wraps(test)
        def wrapped(): pass

        if not hasattr(wrapped, '__wrapped__'):
            # Python 3.2 added this. Without it we cannot unwrap.
            # This is just to satisfy the coverage in unsupported python versions
            wrapped.__wrapped__ = test

        self._common_checks(Injector().inspect(wrapped))

    def test_inject_value(self):
        ij = Injector()
        value = []
        ij.add_value('val', value)
        def test(val, other=inject('val')):
            self.assertTrue(val is other)
            self.assertTrue(val is value)
            val.append(5)
        ij.call_inject(test)
        self.assertEqual([5], value)

    def test_inject_provider(self):
        def provider():
            counter['provider_called'] += 1
            return counter

        def test(c, other=inject('c')):
            self.assertTrue(other is c)
            c['counter_used'] += 1

        counter = Counter()
        ij = Injector()
        ij.add_provider('c', provider)

        ij.call_inject(test)
        self.assertEqual(2, counter['provider_called'])
        self.assertEqual(1, counter['counter_used'])

    def test_inject_provider_decorator(self):
        counter = Counter()
        ij = Injector()

        @ij.provider('c')
        def provider():
            counter['provider_called'] += 1
            return counter

        def test(c, other=inject('c')):
            self.assertTrue(other is c)
            c['counter_used'] += 1

        ij.call_inject(test)
        self.assertEqual(2, counter['provider_called'])
        self.assertEqual(1, counter['counter_used'])

    def test_inject_resolver(self):
        counter = Counter()

        def resolver(keyname='provider_called', increment=1):
            counter['resolver_called'] += 1
            def provider():
                counter[keyname] += increment
                return counter
            return provider

        def test(c, other=inject('c', keyname='special_called', increment=10)):
            self.assertTrue(other is c)
            c['counter_used'] += 1

        ij = Injector()
        ij.add_resolver('c', resolver)

        ij.call_inject(test)
        self.assertEqual(2, counter['resolver_called'])
        self.assertEqual(1, counter['provider_called'])
        self.assertEqual(10, counter['special_called'])
        self.assertEqual(1, counter['counter_used'])

        ij.call_inject(test)
        self.assertEqual(2, counter['resolver_called'])  # !!! Should be cached and not called again
        self.assertEqual(2, counter['provider_called'])
        self.assertEqual(20, counter['special_called'])
        self.assertEqual(2, counter['counter_used'])

    def test_inject_resolver_decorator(self):
        counter = Counter()

        ij = Injector()
        @ij.resolver('c')
        def resolver(keyname='provider_called', increment=1):
            counter['resolver_called'] += 1
            def provider():
                counter[keyname] += increment
                return counter
            return provider

        def test(c, other=inject('c', keyname='special_called', increment=10)):
            self.assertTrue(other is c)
            c['counter_used'] += 1

        ij.call_inject(test)
        self.assertEqual(2, counter['resolver_called'])
        self.assertEqual(1, counter['provider_called'])
        self.assertEqual(10, counter['special_called'])
        self.assertEqual(1, counter['counter_used'])

        ij.call_inject(test)
        self.assertEqual(2, counter['resolver_called'])  # !!! Should be cached and not called again
        self.assertEqual(2, counter['provider_called'])
        self.assertEqual(20, counter['special_called'])
        self.assertEqual(2, counter['counter_used'])

    def test_remove_provider(self):
        ij = Injector()
        ij.add_value('val', 5)
        ij.remove('val')
        def test(val): pass
        with self.assertRaises(InjectError):
            ij.call_inject(test)

    def test_resolver_alias(self):
        counter = Counter()

        def resolver(keyname='provider_called', increment=1):
            counter['resolver_called'] += 1
            def provider():
                counter[keyname] += increment
                return counter
            return provider

        def test(a, b, c, d, e, f):
            self.assertTrue(a is b)
            self.assertTrue(a is c)
            self.assertTrue(a is d)
            self.assertTrue(a is e)
            self.assertTrue(a is f)
            a['counter_used'] += 1

        ij = Injector()
        ij.add_resolver('a', resolver, alias="b")
        ij.add_resolver('c', resolver, alias=("d", "e", "f"))

        ij.call_inject(test)
        self.assertEqual(6, counter['resolver_called'])
        self.assertEqual(6, counter['provider_called'])
        self.assertEqual(1, counter['counter_used'])

    def test_wrap_decorator(self):
        ij = Injector()

        @ij.wrap
        def test(a):
            return a

        with self.assertRaises(InjectError):
            test()

        ij.add_value('a', 5)
        self.assertEquals(5, test())
        self.assertEquals(6, test(a=6))


import bottle
class TestBottlePlugin(unittest.TestCase):
    def test_autoinject(self):
        app = bottle.Bottle()
        ij = app.install(Plugin())
        @app.get('/')
        def get_route(req, res, injector):
            self.assertEquals(bottle.reqest, req)
            self.assertEquals(bottle.response, res)
            self.assertEquals(ij, injector)

if __name__ == '__main__':
    unittest.main()
