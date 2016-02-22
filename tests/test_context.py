import pytest
from texas.context import Context


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
    both = context.include("root", "layer")

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
    layer = context.include("layer")
    layer_nested = context.include("layer.nested")

    layer_nested["sentinel"] = "value"

    # .include returns a ContextView, not the underlying dict
    assert layer["nested"] is not layer_nested
    assert context.get_context("layer.nested") is layer_nested.contexts[-1]

    assert layer["nested.sentinel"] == layer_nested["sentinel"]


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


def test_view_overlap_mapping(context):
    """
    When iterating a view, overlapping keys are available if the
    top context's value is a mapping.
    """
    context.include("bottom")["key.nested.dicts"] = "bottom_value"
    context.include("top")["key.also.nested"] = "top_value"
    both = context.include("bottom", "top")

    expected_dict = {
        "key": {
            "also": {
                "nested": "top_value"
            },
            "nested": {
                "dicts": "bottom_value"
            }
        }
    }
    # Not 100% a dict, since the nested dict is still a ContextView
    partial_dict = dict(both)
    assert partial_dict["key"]["also"]["nested"] == "top_value"
    assert partial_dict["key"]["nested"]["dicts"] == "bottom_value"
    # The kwargs constructor however will happily unroll everything into an
    # actual dict
    assert dict(**both) == expected_dict


def test_snapshot(context):
    """
    snapshot merges all contexts into a single dict.
    """
    context.include("bottom").update(**{
        "shared": {
            "same": "bottom"
        },
        "bottom-only": "bo-value",
        "multi-mix": {
            "bottom": "mmb-value"
        }
    })
    context.include("middle").update(**{
        "shared": {
            "same": "middle",
            "sm-key": {
                "smk-key": "smk-value"
            }
        },
        "multi-mix": "mmm-value"
    })
    context.include("top").update(**{
        "shared": {
            "added": "top"
        },
        "top-only": {
            "to-key": "to-value"
        },
        "multi-mix": {
            "top": "mmt-value"
        }
    })

    expected = {
        "bottom-only": "bo-value",
        "shared": {
            "same": "middle",
            "sm-key": {"smk-key": "smk-value"},
            "added": "top"
        },
        "top-only": {"to-key": "to-value"},
        "multi-mix": {
            "top": "mmt-value",
            "bottom": "mmb-value"
        }
    }
    contexts = context.include("bottom", "middle", "top")
    assert contexts.snapshot == expected
    assert len(contexts) == 4


def test_contextmanager(context):
    path = "foo.bar.baz"
    with context.include("bottom", "top") as both:
        both[path] = "blah"
    assert path not in context.include("bottom")
    assert context.include("top")[path] == "blah"
