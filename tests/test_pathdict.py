import pytest
from texas.path import PathDict


@pytest.fixture
def d():
    return PathDict(path_separator=".")


def test_get_missing(d):
    with pytest.raises(KeyError):
        d["foo"]

    # Fail on first segment of the path
    with pytest.raises(KeyError) as excinfo:
        d["foo.bar.baz"]
    exception = excinfo.value
    assert exception.args == ("foo", )

    d["foo.bar.other"] = "something"

    # Fail on last segment, with full path in KeyError
    with pytest.raises(KeyError) as excinfo:
        d["foo.bar.baz"]
    exception = excinfo.value
    assert exception.args == ("foo.bar.baz", )


def test_del_missing(d):
    with pytest.raises(KeyError):
        del d["foo"]

    # Fail on first segment of the path
    with pytest.raises(KeyError) as excinfo:
        del d["foo.bar.baz"]
    exception = excinfo.value
    assert exception.args == ("foo", )

    d["foo.bar.other"] = "something"

    # Fail on last segment, with full path in KeyError
    with pytest.raises(KeyError) as excinfo:
        del d["foo.bar.baz"]
    exception = excinfo.value
    assert exception.args == ("foo.bar.baz", )


def test_not_a_path(d):
    """
    PathDict doesn't ensure that each segment is a MutableMapping before
    trying to walk the full path
    """
    d["foo.bar"] = "Value"
    with pytest.raises(TypeError):
        d["foo.bar.baz"]


def test_basics(d):
    d["foo"] = "bar"
    assert d["foo"] == "bar"
    del d["foo"]
    assert "foo" not in d


def test_set_path_missing(d):
    """Intermediate dicts created by default"""
    d["foo.bar.baz"] = "blah"
    assert d["foo"]["bar"]["baz"] == "blah"
    assert d["foo.bar.baz"] == "blah"


def test_empty_segments(d):
    """Empty path segments aren't special cased"""
    d["a..b.c"] = "4 deep"

    assert len(d["a"]) == 1
    assert len(d["a"][""]) == 1
    assert len(d["a"][""]["b"]) == 1
    assert d["a"][""]["b"]["c"] == "4 deep"


def test_delete_path(d):
    d["foo.bar.baz"] = "blah"
    del d["foo.bar.baz"]

    assert "baz" not in d["foo.bar"]
    # Empty segments along the path aren't removed
    assert "bar" in d["foo"]


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


def test_as_dict(d, base):
    d.update(base)
    assert dict(d) == base
    assert len(d) == len(base)
