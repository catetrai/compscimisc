primes = [x for x in range(1000, 10000) if not [t for t in range(2, x) if not x % t]]


def multiplication_hash() -> callable:
    from random import randint
    from sys import maxsize
    from math import log2

    a = randint(0, maxsize-1)
    w = 64 if maxsize > 2**32 else 32

    def calc_hash(k: int, m: int) -> int:
        r = int(log2(m))
        return ((a*k) % 2**w) >> (w-r)

    return calc_hash


def universal_hash() -> callable:
    from random import randint, choice

    p = choice(primes)
    a = randint(0, p-1)
    b = randint(0, p-1)

    def calc_hash(k: int, m: int) -> int:
        return ((a*k + b) % p) % m

    return calc_hash


class HackableHashMap(object):

    def __init__(self, prehash_func=None, hash_func=None,
                 init_size=8, load_factor=0.75, growth_rate=2):
        self.prehash_func = prehash_func or hash  # python built-in
        self.hash_func = hash_func or self.division_hash
        self.init_size = init_size
        self.load_factor = load_factor
        self.growth_rate = growth_rate
        self.table = [[] for _ in range(init_size)]
        self.num_items = 0
        self.count_resize = 0
        self.count_collisions = 0

    @staticmethod
    def division_hash(k, m):
        return k % m

    def _calc_idx_for_key(self, key, table_size=None):
        if not table_size:
            table_size = len(self.table)
        # TODO: check if key is hashable
        return self.hash_func(self.prehash_func(key), table_size)

    def _needs_resize(self):
        current_load = self.num_items / len(self.table)
        print(f"current load = {current_load:.2f}")
        return current_load > self.load_factor

    def _resize_table(self):
        # TODO: shrink table size after deletion of items
        new_size = max(2, int(self.num_items * self.growth_rate))
        new_table = [[] for _ in range(new_size)]
        for key, val in self.gen_items():
            idx = self._calc_idx_for_key(key, table_size=new_size)
            new_table[idx].append((key, val))
        print(f"resizing table from {len(self.table)} to {new_size} slots")
        self.table = new_table
        self.count_resize += 1
        return

    def set_item(self, key, val):
        # Check if we need to resize table (based on load factor)
        if self._needs_resize():
            self._resize_table()

        idx = self._calc_idx_for_key(key)
        for j, item in enumerate(self.table[idx]):
            if item[0] == key:  # key already exists
                print(f"key '{key}' already exists - overwriting value")
                self.table[idx][j] = (key, val)
                return
            else:  # keep track of collisions (multiple items in same slot)
                self.count_collisions += 1

        print(f"new key '{key}' - writing value at idx={idx}")
        self.table[idx].append((key, val))
        self.num_items += 1
        return

    def get_item(self, key):
        idx = self._calc_idx_for_key(key)
        for j, item in enumerate(self.table[idx]):
            if item[0] == key:
                return item[1]
        raise KeyError

    def del_item(self, key):
        idx = self._calc_idx_for_key(key)
        for j, item in enumerate(self.table[idx]):
            if item[0] == key:
                print(f"deleting item {item} at idx={idx}")
                self.table[idx].pop(j)
                self.num_items -= 1
                if len(self.table[idx]) > 0:  # slot is non-empty
                    self.count_collisions -= 1
                return
        raise KeyError

    def gen_items(self):
        """Generator of (key, value) tuples, ordered by table index"""
        for slot in self.table:
            for item in slot:
                yield item

    def __str__(self):
        out = ''
        for idx, item in enumerate(self.table):
            out += f'[{idx}]   {item}\n'
        return out
