"""HTTP API surface for the Emperator runtime."""

from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .contract import ContractInfo, get_contract_info


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
        info: ContractInfo = get_contract_info()
        return {
            'contractVersion': info.version,
            'sourcePath': info.source_path,
        }

    return app


app = create_app()
