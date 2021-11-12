#!/usr/bin/env python3
import code
import sys
from pprint import pprint as pp  # noqa: F401

from pycircleci.api import Api


def console():
    """Start a CircleCI client interactive console"""
    _pyver = f"Python {sys.version}"
    _msg = 'Type "man()" to show the Help screen.'
    _title = "(CircleCI client InteractiveConsole)"
    _banner = f"{_pyver}\n{_msg}\n{_title}"

    def man():
        _txt = """
        === CircleCI client Console Help ===

        The following VARIABLES are directly accessible in a CircleCI client session:

        c, client    # an initialized instance of CircleCI Api class
        """
        print(_txt)

    c = client = Api()
    code.interact(banner=_banner, local=dict(globals(), **locals()))


if __name__ == "__main__":
    console()
