import pytest
from texas.context import Context, PathDict


@pytest.fixture
def context():
    return Context()


def test_get(context):
    root = context.include("root")
    layer = context.include("layer")
    both = context.include("root", "layer")

    root["root_key"] = "root_value"
    layer["layer_key"] = "layer_value"
    both["both_key"] = "both_value"

    assert root["root_key"] == "root_value"
    assert "layer_key" not in root
    assert "both_key" not in root

    assert "root_key" not in layer
    assert layer["layer_key"] == "layer_value"
    assert layer["both_key"] == "both_value"

    assert both["root_key"] == "root_value"
    assert both["layer_key"] == "layer_value"
    assert both["both_key"] == "both_value"


def test_del(context):
    root = context.include("root")
    both = root.include("layer")

    root["root_key"] = "root_value"

    with pytest.raises(KeyError):
        del both["root_key"]

    assert "root_key" in both
    del root["root_key"]
    assert "root_key" not in both


def test_unique_names(context):
    layer = context.include("layer")
    also_layer = context.include("layer")

    layer["foo.bar"] = "baz"
    assert also_layer["foo.bar"] == "baz"


def test_path_contexts(context):
    """By default, paths in context names create nested dicts"""
    root = context.include("root")
    root_nested = context.include("root.nested")

    # .include returns a ContextView, not the underlying PathDict
    assert root["nested"] is not root_nested
    # .current returns the PathDict
    assert root["nested"] is root_nested.current


def test_layered_paths(context):
    """include a sub-context and its parent context in the same view"""
    parent = context.include("parent")
    child = context.include("parent.child")
    both = context.include("parent", "parent.child")

    parent["child.by_parent"] = "set_by_parent"
    child["by_child"] = "set_by_child"

    # "by_child" in the child context
    # "child.by_child" in the parent context (fallthrough)
    assert both["by_child"] == "set_by_child"
    assert both["child.by_child"] == "set_by_child"

    # "by_parent" in the child context
    # "child.by_parent" in the parent context (fallthrough)
    assert both["by_parent"] == "set_by_parent"
    assert both["child.by_parent"] == "set_by_parent"


def test_view_iteration(context):
    """iteration and length use all contexts"""
    context.include("bottom")["bottom_key"] = "bottom_value"
    context.include("top")["top_key"] = "top_value"
    both = context.include("bottom", "top")

    expected_dict = {
        "top_key": "top_value",
        "bottom_key": "bottom_value"
    }
    assert dict(both) == expected_dict


def test_view_iteration_overlap(context):
    """
    When iterating a view, overlapping keys take the top context value.

    This means nested dicts get blown away.
    """
    context.include("bottom")["key.nested.dicts"] = "bottom_value"
    context.include("top")["key.also.nested"] = "top_value"
    both = context.include("bottom", "top")

    expected_dict = {
        "key": {
            "also": {
                "nested": "top_value"
            }
            # note that {"nested": {"dicts": "bottom_value"}}
            # is not present.  dict(both) iterates the keys, instead of
            # iterating the items.
        }
    }
    assert dict(both) == expected_dict
    assert dict(**both) == expected_dict


def test_view_include(context):
    """
    include returns a new ContextView with any additional contexts
    on top of the existing ContextView's.
    """
    root = context.include("root")
    root["root_key"] = "root_value"

    layer = root.include("layer")
    assert layer["root_key"] == "root_value"


def test_custom_factory():
    path_dicts_created = 0
    contexts_created = 0

    def expect(contexts, path_dicts):
        assert contexts_created == contexts
        assert path_dicts_created == path_dicts

    def path_factory():
        nonlocal path_dicts_created
        path_dicts_created += 1
        return dict()

    def context_factory():
        nonlocal contexts_created
        contexts_created += 1
        return PathDict(path_factory=path_factory)

    context = Context(factory=context_factory)
    # contexts |
    expect(1, 0)

    context.include("layer")
    # contexts, "layer" |
    expect(2, 0)

    context.include("layer")["foo.bar.baz"] = "blah"
    # contexts, "layer" | "foo", "foo.bar"
    expect(2, 2)

    with context.include("layer") as same_layer:
        same_layer["foo.bar.another"] = "value"
    # existing context, nothing created
    expect(2, 2)
