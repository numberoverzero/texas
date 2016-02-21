import pytest
from texas.merger import merge


@pytest.fixture
def factory():
    return dict


def test_merge_scalar(factory):
    bottom = {
        "scalar": "bottom"
    }
    top = {
        "scalar": "top"
    }
    contexts = [bottom, top]
    path = "scalar"

    assert merge(factory, contexts, path) == "top"
