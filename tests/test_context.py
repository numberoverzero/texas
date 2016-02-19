import pytest
from texas import Context


@pytest.fixture
def ctx():
    return Context()


def test_invalid_root():
    with pytest.raises(ValueError):
        Context(ctx_separator="!", ctx_reserved_prefix="_!_")


def test_init_values():
    base = {
        "a": "b",
        "c": {
            "d": "e"
        }
    }
    context = Context(**base)
    assert context["a"] == "b"
    assert context["c.d"] == "e"


def test_init_prefixed_raises():
    base = {
        "cannot": "use",
        "_": "prefixed",
        "_keys": "."
    }
    with pytest.raises(KeyError):
        Context(**base)


def test_root(ctx):
    assert ctx.g is ctx.current

    ctx["a"] = "b"
    assert ctx["a"] == "b"

    with pytest.raises(KeyError):
        ctx.pop_context()


def test_fallthrough(ctx):
    ctx["root_key"] = "root_value"

    ctx.push_context("layer")
    ctx["layer_key"] = "layer_value"

    # Both keys accessible
    assert ctx["root_key"] == "root_value"
    assert ctx["layer_key"] == "layer_value"

    # Deletes only act on current context
    with pytest.raises(KeyError):
        del ctx["root_key"]

    # Can't access layer_key anymore
    ctx.pop_context()
    assert ctx["root_key"] == "root_value"
    assert "layer_key" not in ctx


def test_pop_name(ctx):
    ctx.push_context("layer1")
    # Success - this is the current context
    ctx.pop_context(name="layer1")

    ctx.push_context("layer2")
    ctx.push_context("layer3")

    # Validation fails, layer2 isn't the current context
    with pytest.raises(KeyError):
        ctx.pop_context(name="layer2")

    # pop unknown context with validation
    with pytest.raises(KeyError):
        ctx.pop_context(name="unknown")


def test_root_protection(ctx):
    with pytest.raises(KeyError):
        ctx["_.no.access"]

    with pytest.raises(KeyError):
        del ctx["_"]

    with pytest.raises(KeyError):
        ctx["_"] = "not allowed"


def test_unique(ctx):
    """context names are unique"""

    ctx.push_context("layer1")
    ctx["foo.bar"] = "baz"

    ctx.pop_context()
    assert "foo.bar" not in ctx

    ctx.push_context("layer1")
    assert ctx["foo.bar"] == "baz"


def test_current_only(ctx):
    """iteration and length are over current context only"""
    ctx["some.root.key"] = "root_value"

    ctx.push_context("layer1")
    ctx["layer_key"] = "layer_value"

    # len, iter look at ctx.current only
    assert len(ctx) == 1
    assert list(ctx.items()) == [("layer_key", "layer_value")]


def test_manager_nesting(ctx):
    ctx["root_key"] = "root_value"
    with ctx("layer1"):
        ctx["layer1_key"] = "layer1_value"
        with ctx("layer2"):
            ctx["layer2_key"] = "layer2_value"
            assert "root_key" in ctx
            assert "layer1_key" in ctx
            assert "layer2_key" in ctx
        # Lost layer2
        assert "root_key" in ctx
        assert "layer1_key" in ctx
        assert "layer2_key" not in ctx
    # Lost layer1, layer2
    assert "root_key" in ctx
    assert "layer1_key" not in ctx
    assert "layer2_key" not in ctx


def test_manager_names(ctx):
    with ctx("layer1"):
        ctx["layer1_key"] = "layer1_value"

    with ctx("layer1", "layer2"):
        ctx["layer2_key"] = "layer2_value"
        assert ctx["layer1_key"] == "layer1_value"

    with ctx("layer1"):
        assert "layer2_key" not in ctx

    with ctx("layer2"):
        assert ctx["layer2_key"] == "layer2_value"


def test_manager_cleanup(ctx):
    try:
        with ctx("layer"):
            ctx["should.not.be"] = "accessible"
            raise RuntimeError()
    except RuntimeError:
        pass

    assert "should.not.be" not in ctx


def test_contextual_path_resolution(ctx):
    """pathed set only touches current context"""
    some_level = dict()
    ctx["some.level"] = some_level

    ctx.push_context("layer1")
    ctx["some.level.thing"] = "value"
    ctx.pop_context()

    assert not some_level


def test_contextual_protection_limit(ctx):
    """modification to mutable values in lower contexts are persisted"""
    some_level = dict()
    ctx["some.level"] = some_level

    ctx.push_context("layer1")
    ctx["some.level"]["thing"] = "value"
    ctx.pop_context()

    # not empty - the ["some.level"] is a get, which passes through.
    # then it's a normal set on ["thing"]
    assert some_level == {"thing": "value"}


def test_root_access(ctx):
    """can modify internal storage through .g"""
    layer1 = ctx.push_context("layer1")

    assert ctx.g["_.g"] is ctx.g
    assert ctx.g["_.current"] is layer1
    assert ctx.g["_.contexts.layer1"] is layer1


def test_current_fallthrough(ctx):
    """current doesn't fall through"""
    ctx["root_key"] = "root_value"

    ctx.push_context("layer1")
    current = ctx.current
    assert "root_key" not in current


def test_init_args(base, more):
    d = Context(base)
    assert d["root.foo.last"] == "value"

    d = Context(**base)
    assert d["root.foo.last"] == "value"

    d = Context(base, **more)
    assert d["root.foo.last"] == "value"
    assert d["more.leaf"] == "value"
