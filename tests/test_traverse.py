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
    on_missing = raise_on_missing

    with pytest.raises(KeyError):
        traverse(root, path, sep=sep, on_missing=on_missing)


def test_traverse_last_missing():
    """no raise on last element missing"""
    inner = {}
    root = {
        "a": {
            "b": inner
        }
    }
    sep = "-"
    path = "a-b-c"
    on_missing = raise_on_missing

    last_node, key = traverse(root, path, sep=sep, on_missing=on_missing)
    assert last_node is inner
    assert key == "c"


def test_traverse_creates():
    created = 0

    def factory():
        nonlocal created
        created += 1
        return dict()

    root = dict()
    sep = "."
    path = "a.b.c"
    on_missing = create_on_missing(factory)

    last_node, key = traverse(root, path, sep=sep, on_missing=on_missing)
    assert created == 2  # a and b
    assert last_node is root["a"]["b"]
    assert not last_node  # empty - c is not inserted
    assert key == "c"
