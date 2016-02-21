import collections.abc

from .traversal import traverse, raise_on_missing, create_on_missing
from .merger import merge

MISSING = object()
DEFAULT_PATH_SEPARATOR = "."


def default_context_factory(path_separator):
    """
    By default, Context creates a PathDict for each context.

    Each of those PathDicts will use regular dicts for storage.
    """
    return lambda: PathDict(path_factory=dict,
                            path_separator=path_separator)


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
        self.update(*args, **kwargs)

    def __setitem__(self, path, value):
        if self._sep not in path:
            self._data[path] = value
        else:
            node, key = traverse(self, path, sep=self._sep,
                                 on_missing=self._create_on_missing)
            node[key] = value

    def __getitem__(self, path):
        if self._sep not in path:
            return self._data[path]
        else:
            node, key = traverse(self, path, sep=self._sep,
                                 on_missing=raise_on_missing)
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
            node, key = traverse(self, path, sep=self._sep,
                                 on_missing=raise_on_missing)
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


class Context:
    """
    Namespaced dicts.

    Create views that include multiple dicts to fall back when getting keys.
    By default, uses PathDict for easily looking up nested values.

    Usage:

        context = Context(path_separator=".")
        root = context.include("root")
        # Missing segments automatically creatd
        root["foo.bar"] = "baz"
        assert root["foo"]["bar"] == "baz"

        # Use as a context manager
        with context.include("other") as other:
            other["key"] = "value"

        # Inspect multiple contexts at once
        with context.include("root", "other") as both:
            assert both["foo.bar"] == "baz"
            assert both["key"] == "value"

            both["only.in.other"] = "both_value"

        # Context names are unique - same "other" as above
        other = context.include("other")

        # Sets only apply in the top-most context
        assert "only.in.other" not in root
        assert other["only.in.other"] == "both_value"
    """
    def __init__(self, factory=None, path_separator=DEFAULT_PATH_SEPARATOR):
        """
        Args:
            factory (Optional(Callable[[], collections.abc.MutableMapping])):
                no-arg function that returns an object that implements the
                mapping interface.  Used to fill missing segments when
                setting values.  Defaults to PathDict.
            path-separator (Optional(str)):
                When factory is missing, this is the path separator passed to
                the PathDict constructor when instantiating new contexts.
        """
        self._factory = factory or default_context_factory(path_separator)
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

    def __repr__(self):  # pragma: no cover
        return "Context(contexts=" + repr(self._contexts) + ")"


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

    @property
    def snapshot(self):
        return {key: merge(dict, self.contexts, key) for key in self}

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
        # Avoid creating an intermediate set/list
        return sum(1 for _ in iter(self))

    def __iter__(self):
        seen = set()
        for context in self.contexts:
            for key in context:
                if key not in seen:
                    seen.add(key)
                    yield key
