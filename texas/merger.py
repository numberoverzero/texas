"""
For the set of contexts [bottom, ..., top]:

The type of each value is determined by the first occurrance (in reverse order)
to be either a mapping (collections.abc.Mapping) or a scalar (anything else).

If the value is a scalar, the first value (again, in reverse order) is used.
If the value is a mapping, all other values in contexts that are ALSO mappings
are merged with the same strategy.  The non-mapping values for that key are
pruned, since there is no way to resolve them.

Because the type (mapping/scalar) of the first occurrance is used, there is
never ambiguity when resolving a conflict.

In each of the examples below, the "top" context is below the "bottom" context,
since the end of a list is the top.

TYPE CONFLICT scalar/mapping: top wins
    {
        "key": "bottom"
    },
    {
        "key": {
            "mapping": "top"
        }
    }
    --> {"mapping": "top"}

TYPE CONFLICT scalar/mapping: top wins
    {
        "key": {
            "mapping": "bottom"
        }
    },
    {
        "key": "top"
    }
    --> "top"

VALUE CONFLICT scalar/scalar: top wins
    {
        "key": "bottom"
    },
    {
        "key": "top"
    }
    --> "top"

VALUE CONFLICT mapping/mapping: merge
    {
        "key": {
            "bottom": "bottom",
            "conflict": "bottom",
        }
    },
    {
        "key": {
            "conflict": "top",
            "top": "top",
        }
    }
    --> {"bottom": "bottom", "conflict": "top", "top": "top"}

VALUE CONFLICT mapping/scalar/mapping: merge mappings, drop scalar
    {
        "key": {
            "bottom": "bottom",
            "conflict": "bottom",
        }
    },
    {
        "key": "scalar"
    },
    {
        "key": {
            "conflict": "top",
            "top": "top"
        }
    }
    --> {"bottom": "bottom", "conflict": "top", "top": "top"}
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
    """Only returns values from containers that have the 'path' key"""
    return [c[path] for c in containers if path in c]


def get_mappings(values):
    return [v for v in values if isinstance(v, collections.abc.Mapping)]


class Resolver:
    def __init__(self, factory, unresolved, output, containers, path):
        # State management.

        # Call to create a new mapping
        self.factory = factory

        # Append to push new resolvers
        self.unresolved = unresolved

        # Mapping - set output[path] to store the resolution
        self.output = output

        # Specific to this resolver, these may be inner dicts.
        # Path will always be a single string, relative to the current
        # container.
        self.containers = containers
        self.path = path

    def resolve(self):
        values = get_values(self.containers, self.path)
        if not values:
            return
        merge_type = MergeType.resolve(values)

        # Scalar - simply return top value.
        # Nothing to push onto the unresolved stack, since
        # this is immediately resolved.
        if merge_type is MergeType.Scalar:
            self.output[self.path] = values[-1]
            return

        # From here on, we're merging mappings.
        # First, let's drop all the non-mapping values, since they're
        # incompatible with the top context's type.
        values = get_mappings(values)

        # Aside from the new output container, we won't actually
        # store any new output values.  Instead, we'll push new
        # Resolvers into the unresolved list, to be processed on the
        # next iteration.
        output = self.output[self.path] = self.factory()

        # We don't want to resolve a key twice, so keep track
        # of which ones have been created
        seen = set()

        for value in values:
            for key in value:
                if key in seen:
                    continue
                seen.add(key)
                # Three things changed from this instance:
                # self.output -> output (moving one level deeper)
                # self.containers -> values (inner values to filter)
                # self.path -> key (key in the next mapping's level)
                resolver = Resolver(self.factory, self.unresolved,
                                    output, values, key)
                self.unresolved.append(resolver)

    def __repr__(self):  # pragma: no cover
        return "Resolver(path={}, containers={})".format(
            self.path, self.containers)


def merge(factory, contexts, path):
    unresolved = []
    output = factory()

    root_resolver = Resolver(factory, unresolved, output, contexts, path)
    unresolved.append(root_resolver)

    while unresolved:
        unresolved.pop().resolve()
    return output[path]
