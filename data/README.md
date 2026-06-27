# data/

This directory holds market data files. All subdirectories are gitignored — only this README is tracked.

```
data/
├── raw/        ← unprocessed data as received from providers
├── processed/  ← normalised, adjusted, and validated data
├── external/   ← reference data from third-party sources
└── cache/      ← ephemeral cached data (safe to delete)
```

**Do not commit market data files.** They are large, may be proprietary, and are reproducible from the Data Engine's historical fetch pipeline.
