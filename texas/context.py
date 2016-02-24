import collections.abc

from .traversal import (
    traverse, first_value,
    raise_on_missing, create_on_missing)
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
    def __init__(self, context_factory=dict, path_separator="."):
        """
        Args:
            context_factory (Callable([], collections.abc.MutableMapping)):
                No-arg function that returns a mapping.  Used to create the
                nested contexts.  Defaults to dict.
            path_separator (Optional(str)):
                This is the path separator passed to the PathDict
                constructor when instantiating new contexts.  Defaults to "."
        """
        self._separator = path_separator
        self._create = create_on_missing(context_factory)
        self._contexts = self._create()

    def get_context(self, path, root=None, create=True):
        if root is None:
            root = self._contexts
        on_missing = self._create if create else raise_on_missing
        return traverse(root, path, self._separator, on_missing)

    def include(self, *names):
        if not names:
            raise ValueError("Must include at least one context")
        contexts = list(self.get_context(name) for name in names)
        return ContextView(self, contexts)


class ContextView(collections.abc.MutableMapping):
    def __init__(self, root, contexts, path=""):
        self._root = root
        self._contexts = contexts
        self._path = path

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

    def absolute_path(self, path):
        if not self._path:
            return path
        return self._path + self._root._separator + path

    def __getitem__(self, path):
        # Have to walk the current context from its root node.
        path = self.absolute_path(path)

        # Raises KeyError if there is no context with the given path
        first = first_value(self._contexts, path, self._root._separator)

        # Since the value of the first context containing the path wasn't
        # a mapping, return that value directly
        if not util.is_mapping(first):
            return first

        # Return another ContextView, with a longer path (one mapping deeper)
        return ContextView(self._root, self._contexts, path)

    def __setitem__(self, path, value):
        # Have to walk the current context from its root node.
        path = self.absolute_path(path)

        context = self._contexts[-1]
        if self._root._separator in path:
            path, last = path.rsplit(self._root._separator, 1)
            # Returns the node that "last": value should go in
            context = self._root.get_context(path, root=context, create=True)
            path = last
        context[path] = value

    def __delitem__(self, path):
        # Have to walk the current context from its root node.
        path = self.absolute_path(path)

        context = self._contexts[-1]
        if self._root._separator in path:
            path, last = path.rsplit(self._root._separator, 1)
            # Returns the node that "last" should be deleted from
            context = self._root.get_context(path, root=context, create=False)
            path = last
        del context[path]

    def __len__(self):
        # Avoid creating an intermediate set/list
        return sum(1 for _ in iter(self))

    def __iter__(self):
        seen = set()
        for context in self._contexts:
            if self._path:
                # Resolve path down to current nesting
                try:
                    context = self._root.get_context(
                        self._path, root=context, create=False)
                except (KeyError, TypeError):
                    # KeyError - no mapping in this context
                    # TypeError - non-mapping value along this context's path
                    context = None
            # The value of context[path] isn't necessarily a mapping, so it
            # shouldn't always yield keys.  It could be another iterable like
            # str, which would do Bad Things.
            if not util.is_mapping(context):
                continue
            for key in context:
                if key not in seen:
                    seen.add(key)
                    yield key
