# Athena Coding Standards

These are the non-negotiable conventions used throughout the Athena codebase. Every file produced by Claude or any engineer must follow all of these.

---

## Python Version and Header

Every source file begins with:
```python
"""Module docstring."""

from __future__ import annotations
```

`from __future__ import annotations` makes all annotations lazy strings (PEP 563). This enables `TYPE_CHECKING` imports and forward references without quotes.

---

## Import Organisation

```python
from __future__ import annotations

# 1. stdlib
import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

# 2. third-party
import structlog

# 3. athena (own package)
from athena.platform.exceptions import AthenaError

# TYPE_CHECKING-only imports (never at runtime)
if TYPE_CHECKING:
    from datetime import datetime
    from athena.features.models import FeatureId
```

**TYPE_CHECKING rule:** If a type is only used in annotations (not called as a constructor, not used as a dict key at runtime), put it in `TYPE_CHECKING`. If it's used at runtime (e.g., `Price(Decimal("100"))`, `FeatureNamespace.TECHNICAL` as a dict key), import it at module level.

---

## Type Annotation Rules

```python
# ✅ Correct
def process(value: object) -> str: ...          # use object, not Any
def get(key: str) -> Instrument | None: ...     # union with None, not Optional
context: dict[str, object] = {}                  # parameterized generics

# ❌ Wrong
from typing import Any, Optional
def process(value: Any) -> str: ...
def get(key: str) -> Optional[Instrument]: ...
```

**No `Any` anywhere.** mypy runs with `--strict` and `disallow_untyped_defs = true`. Every function must have return type annotations.

---

## Frozen Dataclasses (the default for value objects)

```python
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ExperimentId:
    value: UUID
    
    def __post_init__(self) -> None:
        # Validate here. Raise typed domain exceptions, never ValueError directly.
        if self.value is None:
            raise InvalidExperimentError("ExperimentId.value must not be None")
    
    def __str__(self) -> str:
        return str(self.value)
```

**Rules:**
- `frozen=True` on ALL value objects, domain models, and snapshots.
- Validate in `__post_init__`, raise domain-specific exceptions.
- Add `order=True` only when natural ordering is needed (e.g., `FeatureVersion`).
- Use `field(default_factory=frozenset)` for mutable defaults.

---

## Exception Hierarchy

Every domain defines its own root exception inheriting from `AthenaError`:

```python
from athena.platform.exceptions import AthenaError

class MarketDataError(AthenaError):
    """Root exception for all market data domain errors."""

class InvalidBarError(MarketDataError):
    def __init__(self, field: str, value: object, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid bar — {field}={value!r}: {reason}",
            error_code="MDT_001",
            field=field,
            reason=reason,
            **context,
        )
        self.field = field
        self.reason = reason
```

**Rules:**
- Error codes follow `{PREFIX}_{NNN}` format: `EXP_001`, `MDT_003`, `FTR_007`.
- Context kwargs use `**context: object` (not `Any`).
- Store structured attributes on the exception for programmatic access.
- `to_dict()` for log serialisation (inherited from `AthenaError`).

---

## Protocol Interfaces

```python
from typing import Protocol, runtime_checkable, TYPE_CHECKING

@runtime_checkable
class FeatureRegistryProtocol(Protocol):
    """Full read/write registry for FeatureDefinition objects."""
    
    def get(self, feature_id: FeatureId) -> FeatureDefinition:
        """Return the definition for the given feature id.
        
        Args:
            feature_id: The feature to retrieve.
            
        Returns:
            The matching ``FeatureDefinition``.
            
        Raises:
            FeatureNotFoundError: If not registered.
        """
        ...
```

**Rules:**
- `@runtime_checkable` on all Protocols.
- Method bodies are `...` (ellipsis), never `pass`.
- All type imports in `if TYPE_CHECKING:` block since these are annotation-only.
- Google-style docstrings on every method (Args, Returns, Raises).

---

## Google-Style Docstrings

```python
def validate_run(run: ExperimentRun) -> ValidationResult:
    """Validate an ``ExperimentRun`` against domain business rules.

    Checks cross-field consistency that cannot be expressed in any individual
    field's ``__post_init__``.

    Args:
        run: The run to validate.

    Returns:
        A ``ValidationResult`` — valid when no rules are violated.

    Raises:
        Nothing — returns structured failures instead of raising.

    Example::

        result = validate_run(run)
        if not result.is_valid:
            for msg in result.failures:
                log.warning("validation.failure", message=msg)
    """
```

**Rules:**
- Every public class, function, and method gets a docstring.
- First line is a short imperative summary.
- Use ``double backticks`` for inline code references.
- Include `Raises:` section whenever exceptions are possible.
- Use `::` (double colon) before code examples, not triple backticks.

---

## Comments

**Write comments only when the WHY is non-obvious:**

```python
# ✅ Good — explains a non-obvious constraint
# SettlementType.PHYSICAL is used as a default value in CommoditySpec,
# which is evaluated at class definition time (not annotation time).
# Therefore it must be a regular import, not TYPE_CHECKING.
from athena.assets.classification import SettlementType

# ✅ Good — documents an invariant
# Nesting: save/restore pattern ensures outer context is preserved
# when bind_context() is called inside another bind_context() scope.

# ❌ Bad — explains what the code already says
# Import the hash library
import hashlib

# ❌ Bad — references the task/PR
# Added for the RSI feature in Sprint 7
```

---

## Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| Module | `snake_case.py` | `market_state.py` |
| Class | `PascalCase` | `ExperimentRun` |
| Exception | `PascalCase` + `Error` suffix | `InvalidBarError` |
| Protocol | `PascalCase` + `Protocol` suffix | `ClockProtocol` |
| Function/method | `snake_case` | `add_trading_days()` |
| Constant | `UPPER_SNAKE` | `NSE_STANDARD_SCHEDULE` |
| TypeVar | Single letter or `_T_co` for covariant | `T`, `T_co` |
| Private | Single underscore | `_compute_hash()` |

---

## `ValidationResult` Pattern

Validators return structured results, never raise directly:

```python
@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    failures: tuple[str, ...] = ()
    
    @classmethod
    def ok(cls) -> ValidationResult:
        return cls(is_valid=True)
    
    @classmethod
    def failed(cls, *messages: str) -> ValidationResult:
        return cls(is_valid=False, failures=tuple(messages))
    
    def merge(self, other: ValidationResult) -> ValidationResult:
        combined = self.failures + other.failures
        return ValidationResult(is_valid=len(combined) == 0, failures=combined)
```

Use duck-typed stubs in tests to cover validator failure paths that constructors protect from:

```python
class FakeBar:
    open_time = datetime(2025, 1, 15)  # naive — bypasses constructor
    ...

result = validate_ohlcv_bar(FakeBar())  # type: ignore[arg-type]
assert not result.is_valid
```

---

## Testing Standards

```
tests/unit/
├── {domain}/
│   ├── __init__.py
│   ├── conftest.py      ← shared fixtures only
│   ├── test_models.py
│   ├── test_exceptions.py
│   └── ...
```

**Rules:**
- 95%+ coverage on every sprint's new code.
- Use `hypothesis` for property-based tests on financial calculations.
- Use `pytest-asyncio` with `asyncio_mode = "auto"` — no explicit `@pytest.mark.asyncio`.
- Fixtures in `conftest.py`, test logic in `test_*.py`.
- Test class names: `TestClassName` (no `Test` suffix on test methods for the class).
- pytest-style assertions: `assert x == y`, not `self.assertEqual(x, y)`.
- `pytest.raises(SomeError, match=r"pattern")` for exception tests.
- Use `# type: ignore[arg-type]` when passing duck-typed stubs.

---

## `ruff` Configuration Highlights

- `line-length = 100`
- `select = ["E", "W", "F", "I", "N", "UP", "B", "S", "SIM", "TCH", "ANN", "PT", "C90", "RUF", "PERF", "LOG"]`
- `ignore = ["ANN401", "UP046"]`
- `tests/**/*.py` ignores: `["S101", "ANN", "PLR2004", "TC001", "TC003"]`

Key rules to watch:
- `TC001/TC003` — move imports that are annotation-only into `TYPE_CHECKING` block.
- `RUF022` — `__all__` must be sorted (auto-fixed by `ruff check --fix`).
- `PERF401` — use `list.extend()` or generator expressions instead of `append()` in loops.
- `SIM102` — combine nested `if` statements with `and`.
- `B904` — use `raise ... from exc` inside `except` clauses.

---

## StrEnum Pattern

```python
from enum import StrEnum

class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    
    @property
    def is_terminal(self) -> bool:
        return self in (ExperimentStatus.ARCHIVED, ExperimentStatus.CANCELLED)
```

- `StrEnum` values ARE strings: `ExperimentStatus.ACTIVE == "active"` is `True`.
- pydantic validates env vars directly without custom validators.
- Add computed properties for domain-meaningful predicates.

---

## Peer-Layer Cross-Integration via Ports

When domain A needs something from peer domain B:

```python
# In domain A: define what you need as a Protocol
@runtime_checkable
class MarketCalendarPort(Protocol):
    def is_trading_day(self, exchange_id: MarketId, d: date) -> bool: ...
    def next_trading_day(self, exchange_id: MarketId, d: date) -> date: ...

# In the engine layer: wire B's implementation to A's port
# (engines can import from both peers)
calendar_impl = NSETradingCalendar(NullHolidayProvider())
market_service = SomeMarketService(calendar=calendar_impl)  # satisfies MarketCalendarPort
```

Never: `from athena.time.calendar import NSETradingCalendar` inside `athena.market.*`.
