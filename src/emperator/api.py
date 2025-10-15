"""HTTP API surface for the Emperator runtime."""

from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .contract import get_contract_path, load_contract_spec


def create_app() -> FastAPI:
    """Instantiate the FastAPI application with core routes."""
    app = FastAPI(
        title='Emperator Runtime',
        version=__version__,
        summary='Operational interface for Emperator services.',
    )

    @app.get('/healthz', tags=['Meta'])
    def healthz() -> dict[str, str]:
        """Return a simple health indicator."""
        return {'status': 'ok', 'version': __version__}

    @app.get('/contract', tags=['Meta'])
    def contract() -> dict[str, str]:
        """Expose metadata about the current API contract version."""
        spec = load_contract_spec()
        info = spec.get('info', {})
        return {
            'contractVersion': str(info.get('version', 'unknown')),
            'sourcePath': str(get_contract_path(relative=True).as_posix()),
        }

    return app


app = create_app()
