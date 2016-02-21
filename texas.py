import collections.abc
__version__ = "0.3"

MISSING = object()
DEFAULT_PATH_SEPARATOR = "."


def raise_on_missing(sep, visited, **kwargs):
    """Raise the full path of the missing key"""
    raise KeyError(sep.join(visited))


def create_on_missing(factory):
    """
    Returns a function to pass to traverse to create missing nodes.

    Usage
    -----
    # This will insert dicts on missing keys
    root = {}
    path = "hello.world.foo.bar"
    on_missing = create_on_missing(dict)
    node, last = traverse(root, path, sep=".", on_missing=on_missing)
    print(root)  # {"hello": {"world": {"foo": {}}}}
    print(node)  # {}
    print(last)  # "bar"
    assert root["hello"]["world"]["foo"] is node
    """
    def on_missing(**kwargs):
        return factory()
    return on_missing


def default_context_factory():
    """
    By default, Context creates a PathDict for each context.

    Each of those PathDicts will use regular dicts for storage.
    """
    return lambda: PathDict(path_factory=dict,
                            path_separator=DEFAULT_PATH_SEPARATOR)


def traverse(root, path, sep, on_missing=raise_on_missing):
    """
    Returns a (node, key) of the last node in the chain and its key.

    sep: splitting character in the path
    on_missing: func that takes (node, key, visited, sep) and returns a
                new value for the missing key or raises.
    """
    visited = []
    node = root
    *segments, last = path.split(sep)
    for segment in segments:
        # Skip empty segments - collapse "foo..bar.baz" into "foo.bar.baz"
        if not segment:
            continue
        visited.append(segment)
        child = node.get(segment, MISSING)
        if child is MISSING:
            # pass by keyword so functions may ignore variables
            new = on_missing(node=node, key=segment, visited=visited, sep=sep)
            # insert new node if the on_missing function didn't raise
            child = node[segment] = new
        node = child
    return [node, last]


class PathDict(collections.abc.MutableMapping):
    """Path navigable dict, inserts missing nodes during set.

    Args:
        path_separator (Optional[str]):
            string that separates each segment of
            a path.  Defaults to "."
        path_factory (Callable[[], collections.abc.MutableMapping]):
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
        self.update(*args, **kwargs)

    def __setitem__(self, path, value):
        node, key = traverse(self, path, sep=self._sep,
                             on_missing=self._create_on_missing)
        if node is self:
            self._data[key] = value
        else:
            node[key] = value

    def __getitem__(self, path):
        node, key = traverse(self, path, sep=self._sep,
                             on_missing=raise_on_missing)
        if node is self:
            return self._data[key]
        else:
            return node[key]

    def __delitem__(self, path):
        node, key = traverse(self, path, sep=self._sep,
                             on_missing=raise_on_missing)
        if node is self:
            del self._data[key]
        else:
            del node[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):  # pragma: no cover
        return "PathDict(" + repr(dict(self)) + ")"


class Context:
    def __init__(self, factory=None):
        self._factory = factory or default_context_factory()
        self._contexts = self._factory()

    def _get_context(self, name):
        try:
            return self._contexts[name]
        except KeyError:
            context = self._contexts[name] = self._factory()
            return context

    def include(self, *names, contexts=None):
        contexts = list(contexts) if (contexts is not None) else []
        contexts.extend(self._get_context(name) for name in names)
        return ContextView(self, contexts)


class ContextView(collections.abc.MutableMapping):
    def __init__(self, context, contexts):
        self.contexts = contexts
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    @property
    def current(self):
        return self.contexts[-1]

    def include(self, *names):
        return self.context.include(*names, contexts=self.contexts)

    def __getitem__(self, path):
        for context in reversed(self.contexts):
            value = context.get(path, MISSING)
            if value is not MISSING:
                return value
        raise KeyError(path)

    def __setitem__(self, path, value):
        self.current[path] = value

    def __delitem__(self, path):
        del self.current[path]

    def __len__(self):
        return len(self.current)

    def __iter__(self):
        return iter(self.current)
