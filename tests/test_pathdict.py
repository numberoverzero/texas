import pytest
from texas import PathDict


@pytest.fixture
def d():
    return PathDict(path_separator=".")


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
    assert len(d["a"]) == 1
    assert len(d["a"]["b"]) == 1
    assert d["a"]["b"]["c"] == "3 deep"


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


def test_custom_factory():
    created = []

    def factory():
        new = dict()
        created.append(new)
        return new

    d = PathDict(path_separator="!", path_factory=factory)

    # root and foo are created, with "last" a key inside of root!foo
    d["root!foo!last"] = "value"
    assert created == [d["root"], d["root!foo"]]


def test_init_args(base, more):
    d = PathDict(base)
    assert d["root.foo.last"] == "value"

    d = PathDict(**base)
    assert d["root.foo.last"] == "value"

    d = PathDict(base, **more)
    assert d["root.foo.last"] == "value"
    assert d["more.leaf"] == "value"
