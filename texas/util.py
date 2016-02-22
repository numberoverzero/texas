import collections.abc


def is_mapping(value):
    return isinstance(value, collections.abc.Mapping)


def top_value(values, path):
    """top-most value at path, that's not missing"""
    for value in reversed(values):
        try:
            return value[path]
        except KeyError:
            continue
    raise KeyError(path)
