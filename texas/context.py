import collections.abc

from .merger import merge
from .path import PathDict
from .traversal import DEFAULT_SEPARATOR
MISSING = object()


def context_factory(path_separator):
    """
    By default, Context creates a PathDict for each context.

    Each of those PathDicts will use regular dicts for storage.
    """
    return lambda: PathDict(path_factory=dict,
                            path_separator=path_separator)


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
    def __init__(self, path_separator=DEFAULT_SEPARATOR):
        """
        Args:
            path-separator (Optional(str)):
                This is the path separator passed to the PathDict
                constructor when instantiating new contexts.  Defaults to "."
        """
        self._factory = context_factory(path_separator)
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
    def __init__(self, context, contexts, path=None):
        self.contexts = contexts
        self.context = context
        self.path = path or []

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
