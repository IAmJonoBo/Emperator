# ADR-0005: Safety Envelope Design for Automated Code Fixes

**Status:** Accepted\
**Date:** 2025-10-15\
**Deciders:** AI (Copilot), Maintainers\
**Technical Story:** Sprint 5 – Automated Fix & Safety Envelope

## Context

Emperator aims to automatically remediate contract violations by applying code transformations. This automation introduces significant risk:

1. **Correctness Risk:** Transformation could introduce bugs or break functionality
1. **Semantic Risk:** Changes could alter program behavior unintentionally
1. **Test Risk:** Inadequate test coverage could hide regressions
1. **Rollback Risk:** Failed fixes could leave codebase in broken state
1. **Trust Risk:** Developers may distrust automated changes without transparency

Industry examples of automated refactoring:

- **Automated deprecation fixes:** Google's Large Scale Changes (LSC) with automated testing
- **Codemod tools:** Facebook's jscodeshift, LibCST for Python
- **IntelliJ IDEA refactorings:** Extensive automated refactoring with rollback
- **OpenRewrite:** Recipe-based transformations for JVM with verification

Key insight from research: **Automated fixes are only safe when validated through multiple layers** (static analysis, tests, human review for complex changes).

## Decision Drivers

1. **Safety First:** Never apply a fix that breaks tests or introduces new violations
1. **Transparency:** Developers must understand what changes are proposed and why
1. **Rollback Capability:** Must be able to undo any automated change instantly
1. **Risk Stratification:** Different validation requirements for different risk levels
1. **Developer Trust:** Build confidence through provenance and audit trails
1. **Performance:** Validation must complete in reasonable time (\<5min for typical fixes)

## Options Considered

### Option 1: Full Manual Review for All Fixes

**Pros:**

- Maximum safety (human reviews every change)
- No risk of automated bugs
- Developer maintains full control

**Cons:**

- Slow (defeats purpose of automation)
- Scales poorly (100s of violations → 100s of reviews)
- Tedious for trivial fixes (formatting)

**Verdict:** ❌ Rejected – Eliminates automation benefits

### Option 2: Trust-Based Auto-Apply (No Validation)

**Pros:**

- Fast (apply fixes immediately)
- Simple implementation
- No validation overhead

**Cons:**

- High risk of breaking changes
- No safety net for transformer bugs
- Destroys developer trust if issues occur
- Violates "first, do no harm" principle

**Verdict:** ❌ Rejected – Unacceptable risk for production code

### Option 3: Test-Only Validation

**Pros:**

- Fast validation (only run tests)
- Simple model (pass/fail)
- Standard practice in industry

**Cons:**

- Requires high test coverage (not always available)
- Misses static analysis issues (type errors, lint violations)
- Tests might not exercise transformed code
- False confidence if test quality is poor

**Verdict:** ⚠️ Insufficient alone – Necessary but not sufficient

### Option 4: Multi-Layer Safety Envelope (SELECTED)

**Pros:**

- Defense in depth (multiple validation layers)
- Risk-based automation (auto-apply low-risk, review high-risk)
- Combines static analysis, testing, and human judgment
- Rollback capability for recovery
- Audit trail for transparency

**Cons:**

- More complex implementation
- Longer validation time for high-risk changes
- Requires careful tier classification

**Verdict:** ✅ Selected – Best balance of safety, automation, and trust

## Decision

Implement a **tiered safety envelope** with **multi-layer validation** and **automatic rollback**.

### Safety Envelope Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                    Safety Envelope Pipeline                   │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐                                         │
│  │  Risk Tier      │────┐                                    │
│  │  Classification │    │                                    │
│  └─────────────────┘    │                                    │
│         │               │                                    │
│         ▼               ▼                                    │
│  ┌───────────┐    ┌────────────┐                            │
│  │  Tier 0-1 │    │  Tier 2-3  │                            │
│  │  Auto     │    │  Manual    │                            │
│  └───────────┘    └────────────┘                            │
│         │               │                                    │
│         ▼               └──────────┐                         │
│  ┌──────────────────────────────┐ │                         │
│  │   Pre-Fix Validation         │ │                         │
│  │   ✓ Static analysis clean    │ │                         │
│  │   ✓ Tests passing            │ │                         │
│  └──────────────────────────────┘ │                         │
│         │                          │                         │
│         ▼                          │                         │
│  ┌──────────────────────────────┐ │                         │
│  │   Create Snapshot            │ │                         │
│  │   (rollback point)           │ │                         │
│  └──────────────────────────────┘ │                         │
│         │                          │                         │
│         ▼                          │                         │
│  ┌──────────────────────────────┐ │                         │
│  │   Apply Transformation       │ │                         │
│  │   (LibCST / OpenRewrite)     │ │                         │
│  └──────────────────────────────┘ │                         │
│         │                          │                         │
│         ▼                          │                         │
│  ┌──────────────────────────────┐ │                         │
│  │   Post-Fix Validation        │ │                         │
│  │   ✓ Syntax valid             │ │                         │
│  │   ✓ Static analysis clean    │ │                         │
│  │   ✓ No new violations        │ │                         │
│  │   ✓ Tests still pass         │ │                         │
│  │   ✓ Diff scope reasonable    │ │                         │
│  └──────────────────────────────┘ │                         │
│         │                          │                         │
│    ┌────┴────┐                     │                         │
│    ▼         ▼                     ▼                         │
│  ✅ Pass   ❌ Fail          Manual Review                    │
│    │         │                     │                         │
│    ▼         ▼                     ▼                         │
│  Commit  Rollback           Approve/Reject                   │
│                                    │                         │
│                              ┌─────┴─────┐                   │
│                              ▼           ▼                   │
│                           Commit     Discard                 │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Risk Tier Definitions

**Tier 0: Pure Formatting**

- **Scope:** Whitespace, line breaks, import sorting, trailing commas
- **Validation:** Formatter is deterministic (e.g., Ruff, Black)
- **Tests:** None required (no semantic changes)
- **Automation:** Auto-apply without review
- **Rollback:** Not needed (can reformat again if needed)

**Examples:**

- Add trailing comma to multi-line list
- Reformat to 100-character line limit
- Sort imports alphabetically

**Tier 1: Localized Refactors**

- **Scope:** Single function or small module, \<10 lines changed
- **Validation:** Static analysis + unit tests for affected code
- **Tests:** Run tests that cover modified functions
- **Automation:** Auto-apply with test verification
- **Rollback:** Automatic on test failure

**Examples:**

- Rename variable to match naming convention
- Replace `eval()` with `ast.literal_eval()`
- Add type annotation to function signature
- Replace deprecated API call

**Tier 2: Complex Refactors**

- **Scope:** Module-level changes, multiple functions, 10-50 lines changed
- **Validation:** Full test suite + static analysis
- **Tests:** All tests must pass
- **Automation:** Present diff for manual approval
- **Rollback:** Automatic on rejection or test failure

**Examples:**

- Extract method from long function
- Restructure conditional logic
- Move class to different module
- Refactor exception handling

**Tier 3: Architectural Changes**

- **Scope:** Multi-module impact, API changes, >50 lines changed
- **Validation:** Full test suite + integration tests + manual review
- **Tests:** All tests + performance tests
- **Automation:** Flag only, no auto-fix
- **Rollback:** Manual via git revert or rollback plan

**Examples:**

- Split service into multiple services
- Change API signature (breaking change)
- Refactor inheritance hierarchy
- Database schema migration

### Classification Algorithm

```python
def classify_fix(
    finding: CorrelatedFinding,
    proposed_fix: ProposedFix,
    context: CodeContext,
) -> FixClassification:
    """Determine risk tier for proposed fix."""
    
    # Tier 0: Pure formatting?
    if is_formatting_only(proposed_fix):
        return FixClassification(
            tier=RiskTier.TIER_0,
            confidence=1.0,
            reasoning="Formatting-only change",
            auto_apply_allowed=True,
        )
    
    # Count impact
    lines_changed = count_lines_changed(proposed_fix)
    files_affected = count_files_affected(proposed_fix)
    functions_modified = count_functions_modified(proposed_fix)
    test_coverage = get_test_coverage(context, proposed_fix)
    
    # Tier 1: Small, well-tested change?
    if (
        lines_changed <= 10
        and files_affected == 1
        and functions_modified <= 2
        and test_coverage >= 0.9
        and not changes_api_signature(proposed_fix)
    ):
        return FixClassification(
            tier=RiskTier.TIER_1,
            confidence=0.95,
            reasoning="Localized change with high test coverage",
            auto_apply_allowed=True,
            validation_requirements=(
                ValidationCheck.STATIC_ANALYSIS,
                ValidationCheck.UNIT_TESTS,
            ),
        )
    
    # Tier 2: Moderate complexity?
    if (
        lines_changed <= 50
        and files_affected <= 3
        and not changes_api_signature(proposed_fix)
    ):
        return FixClassification(
            tier=RiskTier.TIER_2,
            confidence=0.8,
            reasoning="Moderate-complexity refactor",
            auto_apply_allowed=False,
            requires_manual_review=True,
            validation_requirements=(
                ValidationCheck.STATIC_ANALYSIS,
                ValidationCheck.FULL_TEST_SUITE,
            ),
        )
    
    # Tier 3: High complexity/risk
    return FixClassification(
        tier=RiskTier.TIER_3,
        confidence=0.6,
        reasoning="High-complexity architectural change",
        auto_apply_allowed=False,
        requires_manual_review=True,
        validation_requirements=(
            ValidationCheck.STATIC_ANALYSIS,
            ValidationCheck.FULL_TEST_SUITE,
            ValidationCheck.INTEGRATION_TESTS,
            ValidationCheck.MANUAL_REVIEW,
        ),
    )
```

### Validation Layers

**Layer 1: Pre-Fix Validation**

Ensure starting state is clean:

```python
async def run_pre_validation(context: FixContext) -> ValidationResult:
    """Validate state before applying fix."""
    checks = [
        check_syntax_valid(context.files),
        check_static_analysis_clean(context.files),
        check_tests_passing(context.test_suite),
    ]
    results = await asyncio.gather(*checks)
    return ValidationResult(
        passed=all(r.passed for r in results),
        checks=results,
    )
```

**Layer 2: Transformation Validation**

Ensure transformation is valid:

```python
def validate_transformation(result: TransformResult) -> bool:
    """Check transformation output."""
    for file in result.modified_files:
        # Syntax check
        if not is_valid_syntax(file):
            return False
        
        # Diff scope check
        diff = compute_diff(file.original, file.transformed)
        if diff.lines_changed > result.expected_changes:
            log_warning(f"Unexpected changes in {file}")
            return False
    
    return True
```

**Layer 3: Post-Fix Validation**

Ensure no regressions:

```python
async def run_post_validation(
    context: FixContext,
    applied: TransformResult,
) -> ValidationResult:
    """Validate outcome after applying fix."""
    checks = [
        check_syntax_valid(applied.modified_files),
        check_static_analysis_clean(applied.modified_files),
        check_no_new_violations(applied.modified_files),
        check_tests_passing(context.test_suite),
        check_diff_scope_reasonable(applied),
    ]
    results = await asyncio.gather(*checks)
    return ValidationResult(
        passed=all(r.passed for r in results),
        checks=results,
    )
```

### Rollback Mechanism

**Strategy 1: In-Memory Snapshot (Tier 1)**

```python
@dataclass
class Snapshot:
    """Pre-fix file state."""
    files: dict[Path, bytes]
    timestamp: datetime

def create_snapshot(files: tuple[Path, ...]) -> Snapshot:
    """Capture current state."""
    return Snapshot(
        files={f: f.read_bytes() for f in files},
        timestamp=datetime.now(),
    )

def rollback_snapshot(snapshot: Snapshot) -> None:
    """Restore previous state."""
    for path, content in snapshot.files.items():
        path.write_bytes(content)
```

**Strategy 2: Git Stash (Tier 2)**

```python
def rollback_via_git_stash() -> None:
    """Use git stash for rollback."""
    # Before fix:
    subprocess.run(["git", "stash", "push", "-m", "emperator-fix-snapshot"])
    
    # Apply fix...
    
    # On failure:
    subprocess.run(["git", "stash", "pop"])
```

**Strategy 3: Git Commit + Revert (Tier 3)**

```python
def rollback_via_git_commit() -> None:
    """Create commit then revert on failure."""
    # Apply fix
    subprocess.run(["git", "add", "-A"])
    subprocess.run([
        "git", "commit", "-m",
        "fix: automated fix (Emperator)\n\nWill revert if validation fails"
    ])
    
    # Run validation...
    
    # On failure:
    subprocess.run(["git", "revert", "HEAD", "--no-edit"])
```

### Provenance and Audit Trail

**Commit Message Template:**

```
fix({category}): {short description}

Applied by Emperator v{version}
Rule: {rule_id} ({contract_source})
Transformer: {transformer_name}
Risk Tier: {tier}
Validation: {validation_summary}

Files changed:
{file_list}

Provenance:
- Finding ID: {finding_id}
- Correlation: {confidence} confidence
- Applied: {timestamp}
- Tests: {test_status}
- Review: {review_status}

Co-authored-by: Emperator Bot <emperator@example.com>
```

**Telemetry Event:**

```json
{
  "event": "fix_applied",
  "timestamp": "2025-10-22T14:30:00Z",
  "fix_id": "fix-ban-eval-util-py-42",
  "rule_id": "security.ban-eval",
  "risk_tier": 1,
  "transformer": "DeprecatedAPITransformer",
  "files_changed": ["src/util.py"],
  "lines_changed": 1,
  "validation": {
    "pre_checks": "passed",
    "post_checks": "passed",
    "tests": "passed",
    "duration_seconds": 12.4
  },
  "auto_applied": true,
  "rollback_occurred": false
}
```

## Consequences

### Positive

✅ **Risk Stratification:** Developers understand and can control automation level

✅ **Fail-Safe:** Multiple validation layers catch errors before they reach production

✅ **Rollback Safety:** Any fix can be undone automatically or manually

✅ **Transparency:** Full audit trail builds trust

✅ **Scalability:** Auto-apply Tier 0-1 fixes scales to 1000s of violations

✅ **Developer Experience:** Manual review only for complex changes

### Negative

❌ **Validation Overhead:** Full test suite for Tier 2 can take minutes

❌ **Complexity:** Multi-layer validation requires careful orchestration

❌ **Test Dependency:** Requires good test coverage for Tier 1 auto-apply

### Neutral

⚠️ **Tier Classification Accuracy:** Misclassification could auto-apply risky fix (mitigated by post-validation)

⚠️ **Performance Trade-off:** Safety comes at cost of speed (acceptable trade-off)

## Validation

### Success Criteria (Sprint 5)

- ✅ Tier 0-1 fixes: ≥95% success rate (no rollbacks)
- ✅ Tier 2-3 fixes: 100% reviewed before applying
- ✅ Rollback: 100% success rate
- ✅ False positives: ≤5% (fixes incorrectly classified as higher tier)
- ✅ Validation time: ≤30s for Tier 1, ≤5min for Tier 2

### Test Coverage

- Unit tests for classification algorithm
- Integration tests for full validation pipeline
- Property tests for rollback correctness
- Manual testing on real-world repos

### Monitoring

Track in telemetry:

- Fix success rate by tier
- Rollback frequency and reasons
- Validation time per tier
- Manual approval rate and reasons

## Implementation Phases

### Phase 1 (Sprint 5): Core Safety Envelope

- Risk classifier
- Validation orchestrator
- Rollback manager
- LibCST transformers (Python)

### Phase 2 (Sprint 5.5): Enhanced Validation

- Property-based tests
- Performance regression detection
- Advanced diff analysis

### Phase 3 (Phase 4): AI-Assisted Fixes

- LLM suggestions for Tier 3 changes
- Confidence scoring
- Propose-Rank-Validate loop

## Alternatives Considered for Rollback

### Git Worktree

- **Pro:** Isolated working directory, no stashing needed
- **Con:** Complex setup, not well-known to developers
- **Verdict:** ⚠️ Overkill for Sprint 5, consider for Phase 3

### Copy-on-Write Filesystem

- **Pro:** Instant snapshots, no git dependency
- **Con:** Platform-specific (ZFS, Btrfs), not portable
- **Verdict:** ❌ Not available universally

### Database Transactions

- **Pro:** ACID guarantees, built-in rollback
- **Con:** Requires DB for file storage, performance overhead
- **Verdict:** ❌ Too heavyweight

## Related Decisions

- [ADR-0004: IR Builder Architecture](0004-ir-builder-architecture.md) – IR feeds fix engine
- [ADR-0003: Analyzer Telemetry Architecture](0003-analyzer-telemetry-architecture.md) – Telemetry for fix outcomes
- Future ADR: AI-Assisted Fix Generation (will extend this safety envelope)

## References

- [Google Large Scale Changes](https://abseil.io/resources/swe-book/html/ch22.html)
- [Facebook Codemod Architecture](https://engineering.fb.com/2019/07/02/developer-tools/scaling-static-analyses-at-facebook/)
- [LibCST Documentation](https://libcst.readthedocs.io/)
- [OpenRewrite Documentation](https://docs.openrewrite.org/)
- [Safety in Automated Refactoring Research](https://dl.acm.org/doi/10.1145/3180155.3180242)
- Sprint 5 Planning: `docs/explanation/sprint-5-safety-envelope.md`

______________________________________________________________________

**Status Log:**

- 2025-10-15: Proposed during Sprint 5 planning
- 2025-10-15: Accepted by maintainers for implementation
