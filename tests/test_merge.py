import pytest
from texas.merger import merge


@pytest.fixture
def factory():
    return dict


def test_missing(factory):
    contexts = [
        {
            "something": "bottom"
        },
        {
            "other": "top"
        }
    ]
    path = "missing"
    with pytest.raises(KeyError):
        merge(factory, contexts, path)


def test_empty(factory):
    contexts = [
        {
            "something": "bottom"
        },
        {
            "other": {}
        }
    ]
    path = "other"
    assert merge(factory, contexts, path) == {}


def test_scalar(factory):
    contexts = [
        {
            "scalar": "bottom"
        },
        {
            "scalar": "top"
        }
    ]
    path = "scalar"
    assert merge(factory, contexts, path) == "top"


def test_mapping(factory):
    contexts = [
        {
            "dict": {
                "key": "bottom"
            }
        },
        {
            "dict": {
                "key": "top"
            }
        }
    ]
    path = "dict"
    expected = {"key": "top"}
    assert merge(factory, contexts, path) == expected


def test_conflicts(factory):
    """
    Conflicts:
        Type: when there is a scalar/mapping conflict, the type
            of the last context wins.
        Scalar: when a key has multiple scalar values, the value
            of the last context wins.
        Mapping: when a key has multiple mapping values, the mapping values
            are merged according to the above rules.
    """
    contexts = [
        {
            "dict": {
                "key": "bottom",
                "conflict-scalar": {
                    "mapping": "bottom"
                },
                "conflict-mapping": "scalar"
            }
        },
        {
            "dict": {
                "key": "top",
                "conflict-scalar": "scalar",
                "conflict-mapping": {
                    "mapping": "top"
                }
            }
        }
    ]
    path = "dict"
    expected = {
        "key": "top",
        "conflict-scalar": "scalar",
        "conflict-mapping": {
            "mapping": "top"
        }
    }
    assert merge(factory, contexts, path) == expected


def test_complex(factory):
    bottom = {
        "shared": {
            "same": "bottom"
        },
        "bottom-only": "bo-value",
        "multi-mix": {
            "bottom": "mmb-value"
        }
    }
    middle = {
        "shared": {
            "same": "middle",
            "sm-key": {
                "smk-key": "smk-value"
            }
        },
        "multi-mix": "mmm-value"
    }
    top = {
        "shared": {
            "added": "top"
        },
        "top-only": {
            "to-key": "to-value"
        },
        "multi-mix": {
            "top": "mmt-value"
        }
    }

    expected = {
        # solo-scalar(bottom)
        "bottom-only": "bo-value",

        # multi-merge(bottom, middle, top)
        "shared": {

            # multi-scalar(bottom, middle)
            "same": "middle",

            # solo-merge(middle)
            "sm-key": {
                "smk-key": "smk-value"
            },

            # solor-scalar(top)
            "added": "top"
        },

        # solo-merge(top)
        "top-only": {
            "to-key": "to-value"
        },

        # conflict(bottom, middle, top)
        "multi-mix": {
            "top": "mmt-value",
            "bottom": "mmb-value"
        }
    }

    # Wrap the dicts above in a single "key" so we verify the full contexts
    contexts = [
        {"key": bottom},
        {"key": middle},
        {"key": top}
    ]
    path = "key"
    assert merge(factory, contexts, path) == expected
