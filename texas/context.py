import collections.abc
import functools

from .path import PathDict
from .traversal import DEFAULT_SEPARATOR
from . import util

MISSING = object()


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
    def __init__(self, path_factory=dict, path_separator=DEFAULT_SEPARATOR):
        """
        Args:
            path_factory (Optional(Callable[[],
                          collections.abc.MutableMapping])):
                no-arg function that returns an object that implements the
                mapping interface.  Used to fill missing segments when
                setting values.  Defaults to dict.
            path_separator (Optional(str)):
                This is the path separator passed to the PathDict
                constructor when instantiating new contexts.  Defaults to "."
        """
        self.separator = path_separator
        self.factory = functools.partial(PathDict,
                                         path_factory=path_factory,
                                         path_separator=path_separator)
        self.contexts = self.factory()

    def get_context(self, name):
        try:
            return self.contexts[name]
        except KeyError:
            context = self.contexts[name] = self.factory()
            return context

    def include(self, *names, contexts=None):
        contexts = list(contexts) if (contexts is not None) else []
        contexts.extend(self.get_context(name) for name in names)
        return ContextView(self, contexts)


class ContextView(collections.abc.MutableMapping):
    def __init__(self, root, contexts, path=""):
        self.contexts = contexts
        self.root = root
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    @property
    def snapshot(self):
        snapshot = {}
        for key, value in self.items():
            # Resolve proxies
            if isinstance(value, ContextView):
                value = value.snapshot
            snapshot[key] = value
        return snapshot

    def include(self, *names):
        return self.root.include(*names, contexts=self.contexts)

    def full_path(self, path):
        if not self.path:
            return path
        return self.path + self.root.separator + path

    def __getitem__(self, path):
        path = self.full_path(path)

        # Raises KeyError if there is no context with the given path
        top = util.top_value(self.contexts, path)

        # Since the value of the first context containing the path wasn't
        # a mapping, return that value directly
        if not util.is_mapping(top):
            return top

        # Return another ContextView, with a longer path (one mapping deeper)
        return ContextView(self.root, self.contexts, path)

    def __setitem__(self, path, value):
        self.contexts[-1][path] = value

    def __delitem__(self, path):
        del self.contexts[-1][path]

    def __len__(self):
        # Avoid creating an intermediate set/list
        return sum(1 for _ in iter(self))

    def __iter__(self):
        seen = set()
        for context in self.contexts:
            if self.path:
                # Resolve path down to current nesting
                context = context.get(self.path, {})
            # The value of context[path] isn't necessarily a mapping, so it
            # shouldn't always yield keys.  It could be another iterable like
            # str, which would do Bad Things.
            if not util.is_mapping(context):
                continue
            for key in context:
                if key not in seen:
                    seen.add(key)
                    yield key
