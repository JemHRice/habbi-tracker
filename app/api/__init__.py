"""The HTTP transport layer.

Controllers validate input, call `app.domain`, and shape responses. No business
rule lives here: if a router looks like it is deciding something, the decision
belongs in the domain layer instead.
"""
