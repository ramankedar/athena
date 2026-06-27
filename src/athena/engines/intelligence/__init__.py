"""Intelligence Engine — ML model training, serving, and monitoring.

Status: PLANNED — not implemented in v1.

This package exists to:
    1. Reserve the namespace so future implementation does not require moving modules
    2. Document the intended design so current infrastructure choices account for it
    3. Prevent other engines from taking dependency shortcuts that would
       block the eventual ML integration

Planned responsibilities:
    - Feature store: point-in-time correct feature extraction from tick + OHLCV history
    - Model training pipeline: offline, batch, triggered manually or on schedule
    - Model registry: versioned artefacts with performance metadata
    - Online serving: low-latency inference during market hours via ONNX runtime
    - Monitoring: concept drift detection, prediction calibration tracking

Integration contract:
    The Intelligence Engine will publish SignalGenerated events (same type as
    Research Engine). The Trading Engine consumes signals from both engines
    identically — it does not distinguish ML-based from rule-based signals.

See ARCHITECTURE.md §6.3 for the full design.
"""
