import collections.abc

from .traversal import traverse, raise_on_missing, create_on_missing
DEFAULT_PATH_SEPARATOR = "."


class PathDict(collections.abc.MutableMapping):
    """Path navigable dict, inserts missing nodes during set.

    Args:
        path_separator (Optional[str]):
            string that separates each segment of
            a path.  Defaults to "."
        path_factory (Optional(Callable[[], collections.abc.MutableMapping])):
            no-arg function that returns an object that implements the
            mapping interface.  Used to fill missing segments when
            setting values.  Defaults to dict.

    Usage:

        >>> config = PathDict(path_separator="/")
        >>> config["~/ws/texas"] = ["tox.ini", ".travis.yml"]
        >>> config["~/ws/bloop"] = [".gitignore"]
        >>> print(config["~/ws"])
        {'bloop': ['.gitignore'], 'texas': ['tox.ini', '.travis.yml']}

    """
    def __init__(self, *args,
                 path_separator=DEFAULT_PATH_SEPARATOR,
                 path_factory=dict,
                 **kwargs):
        self._sep = path_separator
        self._data = {}
        self._create_on_missing = create_on_missing(path_factory)
        self._raise_on_missing = raise_on_missing(path_separator)
        self.update(*args, **kwargs)

    def __setitem__(self, path, value):
        if self._sep not in path:
            self._data[path] = value
        else:
            node, key = traverse(self, path.split(self._sep),
                                 on_missing=self._create_on_missing)
            node[key] = value

    def __getitem__(self, path):
        if self._sep not in path:
            return self._data[path]
        else:
            node, key = traverse(self, path.split(self._sep),
                                 on_missing=self._raise_on_missing)
            try:
                return node[key]
            except KeyError:
                # Not raised by traverse above, since it doesn't
                # walk the last segment
                raise KeyError(path)

    def __delitem__(self, path):
        if self._sep not in path:
            del self._data[path]
        else:
            node, key = traverse(self, path.split(self._sep),
                                 on_missing=self._raise_on_missing)
            try:
                del node[key]
            except KeyError:
                # Not raised by traverse above, since it doesn't
                # walk the last segment
                raise KeyError(path)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):  # pragma: no cover
        return "PathDict(" + repr(dict(self)) + ")"
