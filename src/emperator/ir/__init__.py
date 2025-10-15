"""Intermediate Representation (IR) module for polyglot code analysis.

This module provides:
- Tree-sitter-based parsing for multiple languages
- Symbol extraction (functions, classes, imports)
- Incremental caching for performance
- Language-agnostic code representation
"""

from emperator.ir.cache import CacheManager
from emperator.ir.parser import IRBuilder, IRSnapshot, ParsedFile
from emperator.ir.symbols import Symbol, SymbolExtractor, SymbolKind

__all__ = [
    'IRBuilder',
    'ParsedFile',
    'IRSnapshot',
    'Symbol',
    'SymbolKind',
    'SymbolExtractor',
    'CacheManager',
]
