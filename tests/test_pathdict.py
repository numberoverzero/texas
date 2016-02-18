import pytest
from texas import PathDict


@pytest.fixture
def context():
    class Context:
        """Dummy context with a separator"""
        sep = "."
    return Context()


@pytest.fixture
def d(context):
    d = PathDict(context)
    # Spoof single-element context for now
    context.g = d
    return d


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


def test_g_recursion(d, context):
    assert d.g is context.g
    assert d.g.g is d
    assert d.g is d


def test_delete_missing(d):
    with pytest.raises(KeyError):
        del d["foo"]


def test_delete_path(d):
    d["foo.bar.baz"] = "blah"
    del d["foo.bar.baz"]
    assert "baz" not in d["foo.bar"]


def test_contains(d):
    d["foo.bar.baz"] = "blah"
    assert "foo" in d
    assert "foo.bar" in d
    assert "foo.missing" not in d
