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

    # Change cli's root
    cli["src.root"] = "~/other"

    # Doesn't change the underlying environment root
    environment["src.root"]  # ~/pics

    # Modifies cli, which is the top context in config
    del config["src.root"]
    config["src.root"]  # ~/pics

    # Snapshot the contexts into a single dict for use in modules that
    # typecheck against dict (instead of collections.abc.Mapping)
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

This even works with individual path segments, since ContextView returns
proxies against the underlying mapping objects::

    config["src"]  # <texas.context.ContextView at ... >
    config["src"]["type"]  # "jpg"

Setting values only applies to the top context in the view, so the value in
bottom is still the same::

    assert bottom["key"] == "bottom"

This breaks down with mutable values - for instance, this will modify the list
in the bottom context::

    context = texas.Context()
    bottom = context.include("bottom")
    top = context.include("top")
    both = context.include("bottom", "top")

    bottom["list"] = []
    top["list"].append("modified!")

    assert bottom["list"] == ["modified!"]

Snapshot
--------

Context does some heavy lifting to make paths and multiple dicts work together
comfortably.  Unfortunately, some libraries make ``isinstance`` checks against
``dict``, and not ``collections.abc.Mapping``.

This is also useful when passing a ContextView to code that will perform many
lookups in a tight loop.  Because an intermediate lookup on a deeply nested
set of dicts creates one proxy per level (ie.
``something["foo"]["bar"]["baz"]`` creates two proxies for the value
``something["foo.bar.baz"] = "blah"``) it can be a significant speedup to
"snapshot" or bake the ContextView for much faster reading.

Merging dicts in general is a complex problem at best, with many ambiguities.
To simplify things, the following rules are used::

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
not recursive.  A sample file that merges arbitrary iterables of mappings using
the same rules as texas is available
`here <https://gist.github.com/numberoverzero/90a36aef936e6dd5a6c4#file-merge-py>`_.

Context Factory
---------------

By default, texas uses simple ``dict``\s for storage.  However, this can be
customized with the ``context_factory`` function, such as using a
``collections.OrderedDict`` or pre-loading values into the node.

This function is used when creating snapshots, the context root, new contexts,
and intermediate segments when setting values by paths.

::

    created = 0

    def factory():
        global created
        created += 1
        return dict()

    # Root context container
    context = texas.Context(context_factory=factory)
    assert created == 1

    # Including contexts
    ctx = context.include("some-context")
    assert created == 2

    # Segments along a path when setting values
    ctx["foo.bar"] = "value"
    assert created == 3

Internals
---------

Internally, all data is stored in python dicts.  You can inspect the global
state of a context through its ``contexts`` attribute::

    import texas
    context = texas.Context()

    context.include("root.something.or.foo")
    context.include("bar", "and.yet.another.foo", "finally")

    print(context._contexts)

Path traversal is performed by the ``traverse`` function, which only handles
traversal of ``collestions.abc.Mapping``.  Therefore, when a non-mapping value
is expected at the end of a path, the path should be split like so::

    full_path = "foo.bar.baz"
    path, last = full_path.rsplit(".", 1)

    assert path == "foo.bar"
    assert last = "baz"

This allows us to travers a root and create the intermediate ``foo`` and
``bar`` dicts without modifying or inspecting ``baz``::

    from texas.traversal import traverse, create_on_missing

    root = dict()
    full_path = "foo.bar.baz"
    path, key = full_path.rsplit(".", 1)

    node = traverse(root, path, ".", create_on_missing(dict))
    node[key] = "value"

    assert root["foo"]["bar"]["baz"] == "value"
