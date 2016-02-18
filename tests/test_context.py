import pytest
from context import Context


@pytest.fixture
def ctx():
    return Context()


def test_invalid_root():
    with pytest.raises(ValueError):
        Context(ctx_separator="!", ctx_reserved_prefix="_!_")


def test_root(ctx):
    assert ctx.g is ctx.current
    assert ctx.g is ctx.g.g

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


def test_manager_cleanup(ctx):
    try:
        with ctx("layer"):
            ctx["should.not.be"] = "accessible"
            raise RuntimeError()
    except RuntimeError:
        pass

    assert "should.not.be" not in ctx
