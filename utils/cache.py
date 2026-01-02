from collections import OrderedDict


class LRUCache:
    def __init__(self, max_entries: int = 1024) -> None:
        self._max_entries = max_entries
        self._data = OrderedDict()

    def get(self, key):
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key, value) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self._max_entries:
            self._data.popitem(last=False)
