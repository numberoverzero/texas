import pytest
from context import PathDict


class Context:
    """Dummy context with a separator"""
    sep = "."


@pytest.fixture
def context():
    return Context()


@pytest.fixture
def d(context):
    return PathDict(context)


def test_get_missing(d):
    with pytest.raises(KeyError):
        d["foo"]


def test_get_missing_path(d):
    with pytest.raises(KeyError):
        d["foo.bar.baz"]


def test_set(d):
    d["foo"] = "bar"
    assert d["foo"] == "bar"


def test_set_path_missing(d):
    d["foo.bar.baz"] = "blah"
    assert d["foo"]["bar"]["baz"] == "blah"
    assert d["foo.bar.baz"] == "blah"


def test_collapse_empty_path_segments(d):
    path = "a..b.c"
    d[path] = "3 deep"
    print(d.data)
    assert len(d["a"]) == 1
    assert len(d["a"]["b"]) == 1
    assert d["a"]["b"]["c"] == "3 deep"
