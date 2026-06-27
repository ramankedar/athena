# Architecture

The full platform architecture is documented in [`ARCHITECTURE.md`](../ARCHITECTURE.md) at the repository root.

This page provides quick navigation links into the key sections.

## Five-Engine Model

| Engine | Module | Status |
|--------|--------|--------|
| Data | `athena.engines.data` | Planned |
| Research | `athena.engines.research` | Planned |
| Intelligence | `athena.engines.intelligence` | Future |
| Trading | `athena.engines.trading` | Planned |
| Governance | `athena.engines.governance` | Planned |

## Dependency Rules

```
athena.interfaces → athena.engines → athena.shared → athena.core
```

`athena.core` has zero external imports. Engine peers never import each other.
Enforced by `import-linter` in CI.
