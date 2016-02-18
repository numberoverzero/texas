Pure python.  Path keys.  ChainedMap on steroids.

Installation
============

Pure python.

::

    pip install texas

Usage
=====

Contexts are python dictionaries with path lookups::

    import texas

    context = texas.Context()

    # normal dictionary operations
    context["foo"] = "bar"
    assert "bar" == context["foo"]
    del context["foo"]

    # paths
    context["foo.bar"] = "baz"
    assert "baz" == context["foo.bar"]
    del context["foo.bar"]

    # length, iteration
    n = 10
    context.update((i, i+1) for i in range(n))
    assert len(context) == n

    for key, value in context.items():
        assert key + 1 == value


But they also track contextual changes::

    ctx = texas.Context()
    ctx["root.layer.key"] = "root_value"

    with ctx("layer1"):
        # read through
        assert "root_value" == ctx["root.layer.key"]
        # local to layer1
        ctx["layer1.key"] = "layer1_value"

    # layer1 not active
    assert "layer1.key" not in ctx

    # manually push layer1 back on
    ctx.push_context("layer1")
    assert "layer1_value" == ctx["layer1.key"]
    ctx.pop_context()

    # global context
    # WARNING: be careful in the reserved area of the global root,
    # as you can break the context tracking.
    assert ctx.g is ctx.g["_.root"]
    assert ctx.g is ctx.g["_.current"]

    # all contexts are available from the root node
    assert "layer1" in ctx.g["_.contexts"]
    assert "layer1.key" in ctx.g["_.contexts.layer1"]
    assert "layer1_value" == ctx.g["_.contexts.layer1.layer1.key"]

    # nesting:
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
