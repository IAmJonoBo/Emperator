"""Emperator core package.

Populate this package with the primary runtime modules.
Keep public APIs explicit in ``__all__`` where practical.
"""

from __future__ import annotations

__version__ = '0.1.0'

from .api import create_app  # noqa: F401
from .contract import get_contract_path, load_contract_spec  # noqa: F401

__all__: list[str] = [
    '__version__',
    'create_app',
    'get_contract_path',
    'load_contract_spec',
]
