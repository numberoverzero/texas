from .util import is_mapping
MISSING = object()
BAD_PATH = "Expected a mapping in {} at {} but didn't find one"


def raise_on_missing(visited, separator, **kwargs):
    """Raise the full path of the missing key"""
    raise KeyError(separator.join(visited))


def create_on_missing(factory):
    """Returns a traverse function that creates missing nodes."""
    def on_missing(**kwargs):
        return factory()
    return on_missing


def traverse(root, path, separator, on_missing):
    """
    Returns the last node in the path.

    on_missing: func that takes (node, key, visited, sep) and returns a
                new value for the missing key or raises.
    """
    visited = []
    node = root
    for segment in path.split(separator):
        visited.append(segment)
        child = node.get(segment, MISSING)
        # Don't try to follow path into iterables like str
        if child is MISSING:
            # pass by keyword so functions may ignore variables
            new = on_missing(node=node, segment=segment, separator=separator,
                             visited=visited)
            # insert new node if the on_missing function didn't raise
            child = node[segment] = new
        if not is_mapping(child):
            raise TypeError(BAD_PATH.format(root, path))
        node = child
    return node


def first_value(values, path, separator):
    """top-most value at path, that's not missing"""
    # No need to traverse, just check the immediate value
    if separator not in path:
        return _simple_first(values, path)

    # We don't want mapping check on the last lookup,
    # since context["last"] is likely a non-mapping value
    path, last = path.rsplit(separator, 1)
    for value in reversed(values):
        try:
            context = traverse(value, path, separator, raise_on_missing)
            return context[last]
        except (KeyError, TypeError):
            # KeyError - no mapping in this context
            # TypeError - non-mapping value along this context's path
            continue
    raise KeyError(path)


def _simple_first(values, path):
    for value in reversed(values):
        try:
            return value[path]
        except KeyError:
            continue
    raise KeyError(path)
