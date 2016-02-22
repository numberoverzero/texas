import collections.abc


def is_mapping(value):
    return isinstance(value, collections.abc.Mapping)
