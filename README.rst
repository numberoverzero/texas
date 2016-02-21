.. image:: https://img.shields.io/travis/numberoverzero/texas/master.svg?style=flat-square
    :target: https://travis-ci.org/numberoverzero/texas
.. image:: https://img.shields.io/coveralls/numberoverzero/texas/master.svg?style=flat-square
    :target: https://coveralls.io/github/numberoverzero/texas
.. image:: https://img.shields.io/pypi/v/texas.svg?style=flat-square
    :target: https://pypi.python.org/pypi/texas
.. image:: https://img.shields.io/github/issues-raw/numberoverzero/texas.svg?style=flat-square
    :target: https://github.com/numberoverzero/texas/issues
.. image:: https://img.shields.io/pypi/l/texas.svg?style=flat-square
    :target: https://github.com/numberoverzero/texas/blob/master/LICENSE

Pure python.  Path keys.  ChainedMap on steroids.

Installation
============

::

    pip install texas

Quick Start
===========

::

    import texas

    context = texas.Context()

    environment = context.include("environment")
    cli = context.include("cli")

    config = context.include("environment", "cli")

    environment["src.root"] = "~/pics"
    cli["src.type"] = "jpg"

    config["src.root"]  # ~/pics
    config["src.type"]  # jpg

    # Change current configuration's root
    config["src.root"] = "~/other"

    # Doesn't change the underlying environment root
    environment["src.root"]  # ~/pics

    # Doesn't change environment, changes what config finds
    del config["src.root"]
    config["src.root"]  # ~/pics


    # Snapshot the contexts into a single dict for use in other modules
    # (like jinja, for templating)
    import pprint
    pprint.pprint(config.snapshot)
    # {
    #     "src": {
    #         "root": "~/pics",
    #         "type": "jpg"
    #     }
    # }

Usage
=====

Contexts are namespaced python dictionaries with (configurable) path lookups::

    import texas

    context = texas.Context()
    # Single context
    root = context.include("root")

    # normal dictionary operations
    root["foo"] = "bar"
    assert "bar" == root["foo"]
    del root["foo"]

    # paths
    root["foo.bar"] = "baz"
    assert "baz" == root["foo.bar"]
    del root["foo.bar"]

Include
-------

Include takes a variable number of context names to load into a view::

    bottom = context.include("bottom")
    top = context.include("top")

    both = context.include("bottom", "top")

This can be used to create a priority when looking up values.  The top of the
context stack will be checked for a key first, then the next, until a context
with the given key is found::

    bottom["key"] = "bottom"
    assert both["key"] == "bottom"

    top["key"] = "top"
    assert both["key"] == "top"

Combined with paths, this can be very powerful for configuration management::

    context = texas.Context()
    env = context.include("env")
    cli = context.include("cli")
    config = context.include("env", "cli")

    env["src.root"] = "~/pics"
    cli["src.type"] = "jpg"

    assert config["src.root"] == "~/pics"
    assert config["src.type"] == "jpg"

Note that this doesn't work with individual path segments::

    # KeyError - "src" is found in the cli context,
    # which doesn't have a value for "type"
    config["src"]["type"]

This is because the ContextView delegates the resolution of the entire path to
each context, instead of trying to resolve each segment within each context.

Setting values only applies to the top context in the view, so the value in
bottom is still the same::

    assert bottom["key"] == "bottom"

This breaks down with mutable values - for instance, this will modify the list
in the bottom context:

    context = texas.Context()
    bottom = context.include("bottom")
    top = context.include("top")
    both = context.include("bottom", "top")

    bottom["list"] = []
    top["list"].append("modified!")

    assert bottom["list"] == ["modified!"]

Nesting Includes
----------------

Creating a new ContextView from an existing ContextView will ensure all the
contexts in the original are also in the new::

    context = texas.Context()

    parent_view = context.include("parent1, parent2")
    child_view = parent_view.include("child1, child2")

    # parent view has the contexts ["parent1", "parent2"]
    # child view has the contexts ["parent1", "parent2", "child1", "child2"]

From an existing ContextView, it's also possible to create a new view
**without** the current contexts::

    config = texas.Context()

    parent_view = config.include("parent1, parent2")

    # parent_view.context refers to `config`
    child_view = parent_view.context.include("child1, child2")

    # child view has the contexts ["child1", "child2"]

Snapshot
--------

Context does some heavy lifting to make paths and multiple dicts work together
comfortably.  Unfortunately, this doesn't work with code that converts the
ContextView into a dict.

Merging dicts in general is a complex problem at best, with many ambiguities.
To simplify things, (check out texas/merger.py to see the "simple" case) the
following rules are used::

    (1) For every key in each context, the top-most[0] context that contains
        that key will determine if the value will be used directly, or merged
        with other contexts.
    (2) If that value is a collections.abc.Mapping, the value of that key in
        each context that contains that key will be merged.
        (A) If there is a context with that key whose value is NOT a mapping,
            its value will be ignored.
        (B) If that value is NOT a collections.abc.Mapping, the value will be
            used directly and no merging occurs[1].
    3) These rules are applied recursively[2] for any nested mappings.

The "top-most context that contains that key" is not always the top context.
In the following, the bottom context is the only one that contains the key
"bottom"::

    {
        "bottom": "bottom-value"
    },
    {
        "top": "top-value"
    }

    Snapshot:

    {
        "bottom": "bottom-value",
        "top": "top-value"
    }

When there is a conflict in type (mapping, non-mapping) the top-most context
determines the type.  For example, this will take the mapping values from
bottom and top, but not middle (whose value is not a mapping)::

    {
        "key": {
            "bottom": "bottom-value"
        }
    },
    {
        "key": ["middle", "non", "mapping"]
    },
    {
        "key": {
            "top": "top-value"
        }
    }

    Snapshot:

    {
        "key": {
            "bottom": "bottom-value",
            "top": "top-value"
        }
    }

While snapshot applies its rules recursively to mappings, the implementation is
not recursive.  See texas/merger.py for details.

Current
-------

To get the top-most context in a ContextView, use ``current``::

    config = texas.Context()
    env = context.include("env")
    cli = context.include("cli")
    config = context.include("env", "cli")

    env["key"] = "env"

    # config falls through cli to env to find "key"
    assert "key" in config

    # Only look at the top context for config
    cli_only = config.current
    assert "key" not in cli_only

    assert config.current is cli.current

Context Factory
---------------

To use PathDict with a different separator, pass ``path_separator``::

    context = texas.Context(path_separator="-")

To use ``dict`` instead of ``PathDict`` for contexts, pass a factory::

    context = texas.Context(factory=dict)

Any no-arg function that returns a ``collections.abc.MutableMapping`` is fine::

    import arrow
    context_id = 0

    def create_context():
        nonlocal context_id
        context_id += 1

        base_data = {
            "created": arrow.now(),
            "id": context_id
        }

        # Normal dict interface, including *args/**kwargs init
        return texas.PathDict(base_data, path_separator=".")

    context = texas.Context(factory=create_context)

    # First context will have id 2 since texas.Context
    # uses an instance from the factory for its storage
    root = context.include("root")
    root["id"]  # 2
