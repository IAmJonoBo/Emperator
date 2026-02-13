"""Emperator core package.

Populate this package with the primary runtime modules.
Keep public APIs explicit in ``__all__`` where practical.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .api import create_app
from .contract import (
    ContractInfo,
    ContractValidationResult,
    get_contract_info,
    get_contract_path,
    load_contract_spec,
    validate_contract_spec,
)

__all__: list[str] = [
    "ContractInfo",
    "ContractValidationResult",
    "__version__",
    "create_app",
    "get_contract_info",
    "get_contract_path",
    "load_contract_spec",
    "validate_contract_spec",
]
