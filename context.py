import collections.abc
import contextlib
__version__ = "0.1"

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


def traverse(root, path, sep=".", on_missing=raise_on_missing):
    """ returns a (node, key) of the last node in the chain and its key.

        sep: splitting character in the path
        on_missing: func that takes (node, key, visited, sep) and returns a
                    new value for the missing key or raises.
    """
    visited = []
    node = root
    *segments, last = path.split(sep)
    for segment in segments:
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
    data = None
    context = None
    generate = None

    def __init__(self, context, **kwargs):
        self.data = self.update(kwargs)
        self.context = context
        self.create_on_missing = create_on_missing(
            lambda: PathDict(self.context))

    @property
    def g(self):
        return self.context.g

    def __setitem__(self, path, value):
        node, key = traverse(self, path, sep=self.context.sep,
                             on_missing=self.create_on_missing)
        node[key] = value

    def __getitem__(self, path):
        node, key = traverse(self, path, sep=self.context.sep,
                             on_missing=raise_on_missing)
        return node[key]

    def __delitem__(self, path):
        node, key = traverse(self, path, sep=self.context.sep,
                             on_missing=raise_on_missing)
        del node[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


class Context(collections.abc.MutableMapping):
    sep = None
    pre = None

    def __init__(self, ctx_separator, ctx_reserved_prefix, **kwargs):
        if ctx_separator in ctx_reserved_prefix:
            raise ILLEGAL_PREFIX
        self.sep = ctx_separator
        self.pre = ctx_reserved_prefix

        root = PathDict(self, **kwargs)
        root[self.pre]["root"] = root
        root[self.pre]["current"] = root
        self._dicts = [root]

    @property
    def g(self):
        """root dict, permanently store values"""
        return self._dicts[0]

    @property
    def current(self):
        return self._dicts[-1]

    @contextlib.contextmanager
    def __call__(self, name):
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
        local = self._push(name)
        yield local
        self._pop()

    def _push(self, name):
        local = PathDict(self)
        # Store the dict in _.contexts.[name]
        #                   _.current
        self.g[self.pre]["contexts"][name] = local
        self.g[self.pre]["current"] = local
        self._dicts.append(local)
        return local

    def _pop(self):
        if len(self._dicts) == 1:
            raise KeyError("Can't pop root context")
        self._dicts.pop()
        self.g[self.pre]["current"] = self._dicts[-1]

    def __setitem__(self, path, value):
        # Disallow modifying the root by accident
        if path.startswith(self.pre) and (self.current is self.g):
            raise CANNOT_MODIFY_ROOT
        self.current[path] = value

    def __getitem__(self, path):
        for ctx in reversed(self._dicts):
            value = ctx.get(path, MISSING)
            if value is not MISSING:
                return value
        raise KeyError(path)

    def __delitem__(self, path):
        if path.startswith(self.pre) and (self.current is self.g):
            raise CANNOT_MODIFY_ROOT
        del self.current[path]

    def __len__(self):
        return len(self.current)

    def __iter__(self):
        return iter(self.current)
