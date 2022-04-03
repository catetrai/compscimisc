import unittest
from random import randint

from HackableHashMap import HackableHashMap, multiplication_hash, universal_hash


class TestHackableHashMap(unittest.TestCase):
    def setUp(self):
        self.m = HackableHashMap()

    def test_num_items(self):
        self.m.set_item('a', 1)
        self.m.set_item('b', 2)
        self.m.set_item('b', 3)
        self.assertEqual(2, self.m.num_items)

    def test_count_resize(self):
        self.m._resize_table()
        self.m._resize_table()
        self.assertEqual(2, self.m.count_resize)

    def test_resize_table(self):
        self.m.set_item(0, 1)
        self.m.set_item(2, 2)
        self.m.set_item(8, 3)
        items_before_resize = set([item for item in self.m.gen_items()])
        # Trigger a resize with an ad-hoc growth size
        self.m.growth_rate = 5
        self.m._resize_table()
        items_after_resize = set([item for item in self.m.gen_items()])
        self.assertSetEqual(items_before_resize, items_after_resize)

    def test_get_existing_item(self):
        self.m.set_item('b', 2)
        try:
            self.assertEqual(2, self.m.get_item('b'))
        except KeyError:
            self.fail('Existing key not found.')

    def test_get_nonexistent_item(self):
        with self.assertRaises(KeyError):
            self.m.get_item('dummy')

    def test_del_existing_item(self):
        self.m.set_item('b', 2)
        try:
            self.m.del_item('b')
        except KeyError:
            self.fail('Existing key not found.')
        with self.assertRaises(KeyError):
            self.m.get_item('b')

    def test_del_nonexistent_item(self):
        with self.assertRaises(KeyError):
            self.m.del_item('b')


class TestHackableHashMapThrashingParams(TestHackableHashMap):
    def setUp(self):
        self.m = HackableHashMap(init_size=3, load_factor=0.2, growth_rate=5)


class TestHackableHashMapBadPreHashFunc(TestHackableHashMap):
    def setUp(self):
        def rand_prehash_func(k):
            """Bad - will return a new random index for the same key!"""
            return randint(0, 1000)
        self.m = HackableHashMap(prehash_func=rand_prehash_func)


class TestHackableHashMapMultiplicationHash(TestHackableHashMap):
    def setUp(self):
        self.m = HackableHashMap(hash_func=multiplication_hash())


class TestHackableHashMapUniversalHash(TestHackableHashMap):
    def setUp(self):
        self.m = HackableHashMap(hash_func=universal_hash())


if __name__ == '__main__':
    unittest.main()
