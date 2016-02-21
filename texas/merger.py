"""
[
    # Bottom==================================================================
    {
        "shared": {
            "same": "bottom"
        },
        "bottom-only": "bo-value",
        "multi-mix": {
            "bottom": "mmb-value"
        }
    }

    # Next ===================================================================
    {
        "shared": {
            "same": "next",
            "sn-key": {
                "snk-key": "snk-value"
            }
        },
        "multi-mix": "mmn-value""
    }

    # Top ====================================================================
    {
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
]


# Combined ===================================================================
{
    # solo-scalar(bottom)
    "bottom-only": "bo-value",

    # multi-merge(bottom, next, top)
    "shared": {

        # multi-scalar(bottom, next)
        "same": "next",

        # solo-merge(next)
        "sn-key": {
            "snk-key": "snk-value"
        },

        # solor-scalar(top)
        "added": "top"
    },

    # solo-merge(top)
    "top-only": {
        "to-key": "to-value"
    },

    # conflict(bottom, next, top)
    "multi-mix": {
        "top": "mmt-value",
        "bottom": "mmb-value"
    }
}
"""
import collections.abc
import enum


class MergeType(enum.Enum):
    Scalar = 0
    Mapping = 1

    @classmethod
    def resolve(cls, values):
        decider = values[-1]
        if isinstance(decider, collections.abc.Mapping):
            return cls.Mapping
        return cls.Scalar


def get_values(containers, path):
    return [c[path] for c in containers if path in c]


class Resolver:
    def __init__(self, containers, path, unresolved, output):
        self.containers = containers
        self.path = path
        self.unresolved = unresolved
        self.output = output

    def resolve(self):
        values = get_values(self.containers, self.path)
        merge_type = MergeType.resolve(values)

        # Scalar - simply return top value.
        # Nothing to push onto the unresolved stack, since
        # this is immediately resolved.
        if merge_type is MergeType.Scalar:
            self.output[self.path] = values[-1]


def merge(factory, contexts, path):
    unresolved = []
    output = factory()

    root_resolver = Resolver(contexts, path, unresolved, output)
    unresolved.append(root_resolver)

    while unresolved:
        resolver = unresolved.pop()
        resolver.resolve()
    return output[path]
