"""Intermediate Representation (IR) module for polyglot code analysis.

This module provides:
- Tree-sitter-based parsing for multiple languages
- Symbol extraction (functions, classes, imports)
- Incremental caching for performance
- Language-agnostic code representation
"""

from emperator.ir.parser import IRBuilder, ParsedFile, IRSnapshot
from emperator.ir.symbols import Symbol, SymbolKind, SymbolExtractor
from emperator.ir.cache import CacheManager

__all__ = [
    'IRBuilder',
    'ParsedFile',
    'IRSnapshot',
    'Symbol',
    'SymbolKind',
    'SymbolExtractor',
    'CacheManager',
]
