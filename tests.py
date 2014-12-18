from collections import Counter
from bottle_inject import inject, Injector
import unittest

class TestInjector(unittest.TestCase):

    def setUp(self):
        self.seq = range(10)

    def test_inspection(self):
        def test(a, _b, c=5, d=inject('x'), e=inject('x2', 'foo', bar="baz"), *f, **g): pass
        results = dict(Injector().inspect(test))
        self.assertEqual(inject('a'), results['a'])
        self.assertEqual(inject('_b'), results['_b'])
        self.assertEqual(None, results.get('c'))
        self.assertEqual(inject('x'), results['d'])
        self.assertEqual(inject('x2', 'foo', bar="baz"), results['e'])
        self.assertEqual(None, results.get('f'))
        self.assertEqual(None, results.get('g'))

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

        def test(c, other=inject('c', 'special_called', increment=10)):
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

if __name__ == '__main__':
    unittest.main()
