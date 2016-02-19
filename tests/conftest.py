import pytest


@pytest.fixture
def base():
    return {
        "root": {
            "foo": {
                "last": "value"
            }
        }
    }


@pytest.fixture
def more():
    return {
        "more": {
            "leaf": "value",
            "branch": {
                "branch leaf": "branch value"
            }
        }
    }
