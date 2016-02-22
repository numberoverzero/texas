import pytest
from texas.traversal import traverse, raise_on_missing, create_on_missing


def test_traverse_raises():
    inner = {}
    root = {
        "a": {
            "b": inner
        }
    }
    sep = "-"
    path = "a-b-c-d"
    with pytest.raises(KeyError):
        traverse(root, path, sep, on_missing=raise_on_missing)


def test_traverse_last_missing():
    """no raise on last element missing"""
    root = {
        "a": {
            "b": {
                "c": {"sentinel": "value"}
            }
        }
    }
    sep = "-"
    path = "a-b-c"
    inner = traverse(root, path, sep, on_missing=raise_on_missing)
    assert inner is root["a"]["b"]["c"]


def test_traverse_creates():
    created = 0

    def factory():
        nonlocal created
        created += 1
        return dict()

    root = dict()
    sep = "."
    path = "a.b.c"
    inner = traverse(root, path, sep, on_missing=create_on_missing(factory))
    assert created == 3  # a and b
    assert root["a"]["b"]["c"] is inner
