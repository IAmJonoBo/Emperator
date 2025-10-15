"""Utilities for aligning the repository layout with the documented blueprint."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ScaffoldAction(Enum):
    """Concrete action that was taken (or planned) for a scaffold item."""

    NONE = 'none'
    CREATED = 'created'
    PLANNED = 'planned'


@dataclass(frozen=True)
class ScaffoldItem:
    """Describes a file system asset that should exist in the repo."""

    relative_path: Path
    description: str
    is_directory: bool = False
    stub: str | None = None


@dataclass
class ScaffoldStatus:
    """Outcome of reconciling a :class:`ScaffoldItem`."""

    item: ScaffoldItem
    path: Path
    exists: bool
    action: ScaffoldAction = ScaffoldAction.NONE

    @property
    def needs_attention(self) -> bool:
        """Whether the asset still requires manual follow-up."""
        return not self.exists and self.action is not ScaffoldAction.CREATED


_SCAFFOLD_ITEMS: tuple[ScaffoldItem, ...] = (
    ScaffoldItem(
        Path('contract'),
        'Contract artifacts workspace',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('contract/policy/policy.rego'),
        'OPA policy bundle',
        stub=(
            'package emperator.policy\n\n# TODO: Encode repository-wide policy rules using Rego.\n'
        ),
    ),
    ScaffoldItem(
        Path('contract/conventions/naming.cue'),
        'CUE conventions contract',
        stub=('// TODO: Declare naming, layout, and validation constraints using CUE.\n'),
    ),
    ScaffoldItem(
        Path('infra/k8s/base'),
        'Kustomize base overlay',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('infra/k8s/base/kustomization.yaml'),
        'Kustomize base manifest',
        stub=(
            '# TODO: Populate shared Kubernetes resources for all environments.\n'
            'apiVersion: kustomize.config.k8s.io/v1beta1\n'
            'kind: Kustomization\n'
            'resources: []\n'
        ),
    ),
    ScaffoldItem(
        Path('infra/k8s/overlays/dev'),
        'Development overlay',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('infra/k8s/overlays/dev/kustomization.yaml'),
        'Development kustomization overlay',
        stub=(
            '# TODO: Reference dev-specific patches and resources.\n'
            'apiVersion: kustomize.config.k8s.io/v1beta1\n'
            'kind: Kustomization\n'
            'resources:\n'
            '  - ../base\n'
            'patches: []\n'
        ),
    ),
    ScaffoldItem(
        Path('infra/k8s/overlays/prod'),
        'Production overlay',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('infra/k8s/overlays/prod/kustomization.yaml'),
        'Production kustomization overlay',
        stub=(
            '# TODO: Reference prod-specific patches and resources.\n'
            'apiVersion: kustomize.config.k8s.io/v1beta1\n'
            'kind: Kustomization\n'
            'resources:\n'
            '  - ../base\n'
            'patches: []\n'
        ),
    ),
    ScaffoldItem(
        Path('infra/terraform/modules'),
        'Reusable Terraform modules',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('infra/terraform/modules/README.md'),
        'Terraform modules index',
        stub=('# Terraform Modules\n\nTODO: Document reusable modules exposed by the platform.\n'),
    ),
    ScaffoldItem(
        Path('infra/terraform/envs/dev'),
        'Terraform dev environment',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('infra/terraform/envs/dev/main.tf'),
        'Terraform dev stack',
        stub=('// TODO: Define dev environment infrastructure resources.\n'),
    ),
    ScaffoldItem(
        Path('infra/terraform/envs/prod'),
        'Terraform prod environment',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('infra/terraform/envs/prod/main.tf'),
        'Terraform prod stack',
        stub=('// TODO: Define production infrastructure resources.\n'),
    ),
    ScaffoldItem(
        Path('rules/semgrep/ruleset.yaml'),
        'Semgrep ruleset stub',
        stub=(
            'rules:\n'
            '  # TODO: Capture Semgrep checks compiled from the Project Contract.\n'
            '  - id: emperator.todo.example\n'
            '    patterns: []\n'
            '    message: TODO describe the rule\n'
            '    severity: INFO\n'
        ),
    ),
    ScaffoldItem(
        Path('rules/codeql/queries'),
        'CodeQL query workspace',
        is_directory=True,
    ),
    ScaffoldItem(
        Path('rules/codeql/queries/EmperatorTodo.ql'),
        'CodeQL query placeholder',
        stub=(
            '/** TODO: Implement a CodeQL query enforcing contract guarantees. */\n'
            'import python\n'
            'from Function f\n'
            "select f, 'Stub query awaiting implementation.'\n"
        ),
    ),
)


def iter_scaffold_items() -> Iterable[ScaffoldItem]:
    """Return the canonical list of scaffold expectations."""
    return iter(_SCAFFOLD_ITEMS)


def audit_structure(project_root: Path) -> list[ScaffoldStatus]:
    """Evaluate the repository layout without modifying the file system."""
    statuses: list[ScaffoldStatus] = []
    for item in iter_scaffold_items():
        path = project_root / item.relative_path
        statuses.append(
            ScaffoldStatus(
                item=item,
                path=path,
                exists=path.exists(),
                action=ScaffoldAction.NONE,
            )
        )
    return statuses


def ensure_structure(project_root: Path, *, dry_run: bool = False) -> list[ScaffoldStatus]:
    """Create missing directories/files described by :data:`_SCAFFOLD_ITEMS`."""
    statuses: list[ScaffoldStatus] = []
    for status in audit_structure(project_root):
        path = status.path
        action = ScaffoldAction.NONE
        if not status.exists:
            action = ScaffoldAction.PLANNED if dry_run else ScaffoldAction.CREATED
            if not dry_run:
                if status.item.is_directory:
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if status.item.stub is not None:
                        path.write_text(status.item.stub, encoding='utf-8')
                    else:
                        path.touch()
            statuses.append(
                ScaffoldStatus(
                    item=status.item,
                    path=path,
                    exists=path.exists(),
                    action=action,
                )
            )
        else:
            statuses.append(status)
    return statuses
