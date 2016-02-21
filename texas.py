import collections.abc
import contextlib
__version__ = "0.2"

MISSING = object()
ILLEGAL_PREFIX = ValueError(
    "reserved_prefix cannot contain the path separator.")
CANNOT_MODIFY_ROOT = KeyError(
    "Cannot modify the root object by direct prefix.  Use context.g instead.")


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


def default_context_factory(separator):
    """
    By default, Context creates a PathDict for each context.

    Each of those PathDicts will use regular dicts for storage.
    """
    return lambda: PathDict(path_factory=dict, path_separator=separator)


def traverse(root, path, sep=".", on_missing=raise_on_missing):
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
    def __init__(self, *args, path_separator=".", path_factory=dict, **kwargs):
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


class Context(collections.abc.MutableMapping):
    def __init__(self,
                 *args,
                 ctx_separator=".",
                 ctx_reserved_prefix="_",
                 ctx_factory=None,
                 **kwargs):
        if ctx_separator in ctx_reserved_prefix:
            raise ILLEGAL_PREFIX
        self._sep = ctx_separator
        self._pre = ctx_reserved_prefix
        self._factory = ctx_factory or default_context_factory(ctx_separator)

        root = self._factory()
        self._dicts = [root]
        # Initial set uses path so all levels are PathDicts
        root[self._pre + self._sep + "g"] = root
        root[self._pre + self._sep + "current"] = root

        self.update(*args, **kwargs)

    @property
    def g(self):
        """root dict, permanently store values"""
        return self._dicts[0]

    @property
    def current(self):
        return self._dicts[-1]

    @contextlib.contextmanager
    def __call__(self, *names):
        """
        Usage
        -----
        ctx = Context(".", "_")
        with ctx("local") as local:
            local["foo"] = "bar"
            local.g["hello.world"] = "!"

        assert "foo" not in ctx
        assert ctx["hello"]["world"] == "!"
        assert ctx["_.ctx.local.foo"] == "bar"
        """
        for name in names:
            self.push_context(name)
        try:
            yield self
        finally:
            for name in reversed(names):
                self.pop_context(name=name)

    def get_context(self, name, create=True):
        """
        Return (optionally create) a context.

        Does not modify the context stack.
        """
        context_path = self._sep.join((self._pre, "contexts", name))
        context = self.g.get(context_path, MISSING)
        if context is MISSING:
            if not create:
                raise KeyError("Unknown context {}".format(name))
            context = self.g[context_path] = self._factory()
        return context

    def push_context(self, name):
        local = self.get_context(name, create=True)
        self.g[self._pre]["current"] = local
        self._dicts.append(local)
        return local

    def pop_context(self, *, name=MISSING):
        if len(self._dicts) == 1:
            raise KeyError("Can't pop root context")
        # When name is provided, validate before popping.
        # Raises KeyError when the requested pop isn't current
        if name is not MISSING:
            if self.get_context(name, create=False) is not self.current:
                raise KeyError("{} is not the current context".format(name))
        old_local = self._dicts.pop()
        self.g[self._pre]["current"] = self._dicts[-1]
        return old_local

    def __setitem__(self, path, value):
        # Disallow modifying the root by accident
        if path.startswith(self._pre) and (self.current is self.g):
            raise CANNOT_MODIFY_ROOT
        self.current[path] = value

    def __getitem__(self, path):
        for ctx in reversed(self._dicts):
            value = ctx.get(path, MISSING)
            if value is not MISSING:
                return value
        raise KeyError(path)

    def __delitem__(self, path):
        if path.startswith(self._pre) and (self.current is self.g):
            raise CANNOT_MODIFY_ROOT
        del self.current[path]

    def __len__(self):
        return len(self.current)

    def __iter__(self):
        return iter(self.current)
