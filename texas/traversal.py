MISSING = object()


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
        visited.append(segment)
        child = node.get(segment, MISSING)
        if child is MISSING:
            # pass by keyword so functions may ignore variables
            new = on_missing(node=node, key=segment, visited=visited, sep=sep)
            # insert new node if the on_missing function didn't raise
            child = node[segment] = new
        node = child
    return [node, last]
