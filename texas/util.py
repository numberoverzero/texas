import collections.abc


def is_mapping(value):
    return isinstance(value, collections.abc.Mapping)


def should_merge(values):
    return is_mapping(values[-1])


def filter_values(values, path):
    for value in values:
        try:
            yield value[path]
        except KeyError:
            continue


def filter_mappings(values):
    for value in values:
        if is_mapping(value):
            yield value
