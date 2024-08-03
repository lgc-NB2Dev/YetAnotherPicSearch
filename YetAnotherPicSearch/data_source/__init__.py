# ruff: noqa: N999


def load_search_func():
    from pathlib import Path

    from cookit import auto_import

    auto_import(Path(__file__).parent, __package__)
