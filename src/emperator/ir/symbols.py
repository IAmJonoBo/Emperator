"""Symbol extraction from Tree-sitter parse trees."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from tree_sitter import Tree


class SymbolKind(Enum):
    """Types of symbols that can be extracted."""

    FUNCTION = 'function'
    CLASS = 'class'
    VARIABLE = 'variable'
    IMPORT = 'import'
    METHOD = 'method'
    PARAMETER = 'parameter'
    ATTRIBUTE = 'attribute'


@dataclass
class Location:
    """Source code location."""

    line: int
    column: int
    end_line: int
    end_column: int

    @classmethod
    def from_node(cls, node: Any) -> 'Location':
        """Create location from Tree-sitter node.

        Args:
            node: Tree-sitter node

        Returns:
            Location object
        """
        return cls(
            line=node.start_point[0],
            column=node.start_point[1],
            end_line=node.end_point[0],
            end_column=node.end_point[1],
        )


@dataclass
class Symbol:
    """Language-agnostic symbol representation."""

    name: str
    kind: SymbolKind
    location: Location
    scope: str = ''
    references: tuple[Location, ...] = ()
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}


class SymbolExtractor:
    """Extract symbols from Tree-sitter CSTs."""

    def extract_symbols(self, tree: Tree, language: str) -> tuple[Symbol, ...]:
        """Use language-specific queries to find symbols.

        Args:
            tree: Parsed Tree-sitter tree
            language: Programming language name

        Returns:
            Tuple of extracted symbols
        """
        if language == 'python':
            return self._extract_python_symbols(tree)
        return ()

    def _extract_python_symbols(self, tree: Tree) -> tuple[Symbol, ...]:
        """Extract symbols from Python parse tree.

        Args:
            tree: Parsed Tree-sitter tree

        Returns:
            Tuple of Python symbols
        """
        symbols = []

        def visit_node(node: Any, scope: str = '') -> None:
            """Visit tree nodes recursively to extract symbols.

            Args:
                node: Current tree node
                scope: Current scope path
            """
            # Function definitions
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = name_node.text.decode('utf-8')
                    symbols.append(
                        Symbol(
                            name=name,
                            kind=SymbolKind.FUNCTION,
                            location=Location.from_node(node),
                            scope=scope,
                        )
                    )
                    # Visit function body with new scope
                    new_scope = f'{scope}.{name}' if scope else name
                    for child in node.children:
                        visit_node(child, new_scope)
                    return

            # Class definitions
            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = name_node.text.decode('utf-8')
                    symbols.append(
                        Symbol(
                            name=name,
                            kind=SymbolKind.CLASS,
                            location=Location.from_node(node),
                            scope=scope,
                        )
                    )
                    # Visit class body with new scope
                    new_scope = f'{scope}.{name}' if scope else name
                    for child in node.children:
                        visit_node(child, new_scope)
                    return

            # Import statements
            if node.type in ('import_statement', 'import_from_statement'):
                # Extract imported names
                for child in node.children:
                    if child.type == 'dotted_name':
                        name = child.text.decode('utf-8')
                        symbols.append(
                            Symbol(
                                name=name,
                                kind=SymbolKind.IMPORT,
                                location=Location.from_node(child),
                                scope=scope,
                            )
                        )
                    elif child.type == 'aliased_import':
                        name_node = child.child_by_field_name('name')
                        if name_node:
                            name = name_node.text.decode('utf-8')
                            symbols.append(
                                Symbol(
                                    name=name,
                                    kind=SymbolKind.IMPORT,
                                    location=Location.from_node(name_node),
                                    scope=scope,
                                )
                            )

            # Continue visiting children
            for child in node.children:
                visit_node(child, scope)

        visit_node(tree.root_node)
        return tuple(symbols)
