import collections.abc


def is_mapping(value):
    return isinstance(value, collections.abc.Mapping)


def filter_values(values, path):
    for value in values:
        try:
            yield value[path]
        except KeyError:
            continue


def filter_mappings(values, path):
    for value in filter_values(values, path):
        if is_mapping(value):
            yield value


def top_value(values, path):
    """top-most value at path, that's not missing"""
    for value in reversed(values):
        try:
            return value[path]
        except KeyError:
            continue
    raise KeyError(path)
