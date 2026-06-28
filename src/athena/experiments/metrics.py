"""Experiment metric value objects.

An ``ExperimentMetric`` captures a single named measurement from a run.
``MetricDirection`` makes comparison semantics explicit: Sharpe ratio is
``HIGHER_IS_BETTER``; max drawdown is ``LOWER_IS_BETTER``; a regime label
is ``NEUTRAL``.

``MetricSnapshot`` is an immutable collection of all metrics for a run,
providing aggregate views (best metric by direction, metric by name lookup).

The ``step`` field on ``ExperimentMetric`` enables iterative logging:
record a metric at each epoch/iteration without creating separate metrics.
Step ``None`` denotes a final scalar (non-iterative) metric.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from athena.experiments.exceptions import InvalidExperimentError


class MetricDirection(StrEnum):
    """Comparison semantics for an experiment metric.

    Attributes:
        HIGHER_IS_BETTER: Larger values are preferred (Sharpe, CAGR, win rate).
        LOWER_IS_BETTER:  Smaller values are preferred (drawdown, turnover, VaR).
        NEUTRAL:          No preference — metric is informational only (regime).
    """

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class ExperimentMetric:
    """A single named measurement from an experiment run.

    Attributes:
        name:               Metric identifier (e.g. ``"sharpe_ratio"``).
        value:              Numeric measurement value.
        direction:          Whether higher or lower is better.
        step:               Iteration/epoch count for iterative metrics.
            ``None`` for final scalar metrics.
        confidence_lower:   Lower bound of a confidence interval. ``None``
            when not computed.
        confidence_upper:   Upper bound of a confidence interval. ``None``
            when not computed.
        tags:               Optional frozenset of tags for grouping metrics.
        description:        Optional human-readable description.

    Raises:
        InvalidExperimentError: If ``name`` is empty, or confidence bounds are
            present but logically invalid.
    """

    name: str
    value: float
    direction: MetricDirection = MetricDirection.NEUTRAL
    step: int | None = None
    confidence_lower: float | None = None
    confidence_upper: float | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidExperimentError("ExperimentMetric.name must not be empty")
        if self.step is not None and self.step < 0:
            raise InvalidExperimentError(f"ExperimentMetric.step must be >= 0, got {self.step}")
        if (
            self.confidence_lower is not None
            and self.confidence_upper is not None
            and self.confidence_lower > self.confidence_upper
        ):
            raise InvalidExperimentError(
                f"confidence_lower ({self.confidence_lower}) must be <= "
                f"confidence_upper ({self.confidence_upper})"
            )

    @property
    def comparison_value(self) -> float:
        """Return a value where LARGER is always BETTER for sorting.

        Negates the value for ``LOWER_IS_BETTER`` metrics so that a single
        descending sort gives the best metric first regardless of direction.

        Returns:
            ``value`` for HIGHER_IS_BETTER/NEUTRAL; ``-value`` for
            LOWER_IS_BETTER.
        """
        if self.direction == MetricDirection.LOWER_IS_BETTER:
            return -self.value
        return self.value

    @property
    def has_confidence_interval(self) -> bool:
        """Return ``True`` when both confidence bounds are provided.

        Returns:
            ``True`` when neither ``confidence_lower`` nor ``confidence_upper``
            is ``None``.
        """
        return self.confidence_lower is not None and self.confidence_upper is not None

    def is_better_than(self, other: ExperimentMetric) -> bool:
        """Return ``True`` if this metric is better than ``other``.

        Compares using ``comparison_value`` (negated for LOWER_IS_BETTER).
        Both metrics must have the same name and direction.

        Args:
            other: The metric to compare against.

        Returns:
            ``True`` when this metric outperforms ``other``.

        Raises:
            InvalidExperimentError: If metrics have different names or
                incompatible directions.
        """
        if self.name != other.name:
            raise InvalidExperimentError(
                f"Cannot compare metrics with different names: {self.name!r} vs {other.name!r}"
            )
        if self.direction != other.direction:
            raise InvalidExperimentError(
                f"Cannot compare metrics with different directions for {self.name!r}"
            )
        return self.comparison_value > other.comparison_value

    def __str__(self) -> str:
        step_str = f"@step={self.step}" if self.step is not None else ""
        return f"Metric({self.name}={self.value}{step_str} [{self.direction.value}])"


@dataclass(frozen=True)
class MetricSnapshot:
    """Immutable collection of all metrics recorded for a run.

    Attributes:
        metrics: Tuple of all ``ExperimentMetric`` objects for the run.

    Raises:
        InvalidExperimentError: If two metrics have the same name and step
            (the combination must be unique).
    """

    metrics: tuple[ExperimentMetric, ...]

    def __post_init__(self) -> None:
        seen: set[tuple[str, int | None]] = set()
        for m in self.metrics:
            key = (m.name, m.step)
            if key in seen:
                raise InvalidExperimentError(f"Duplicate metric: name={m.name!r}, step={m.step!r}")
            seen.add(key)

    @classmethod
    def empty(cls) -> MetricSnapshot:
        """Return an empty metric snapshot.

        Returns:
            A ``MetricSnapshot`` with no metrics.
        """
        return cls(metrics=())

    def get(self, name: str, step: int | None = None) -> ExperimentMetric | None:
        """Return the metric matching name and step, or ``None``.

        Args:
            name: Metric name.
            step: Step number (``None`` for final metrics).

        Returns:
            The matching ``ExperimentMetric``, or ``None``.
        """
        for m in self.metrics:
            if m.name == name and m.step == step:
                return m
        return None

    def all_named(self, name: str) -> tuple[ExperimentMetric, ...]:
        """Return all metrics with the given name (across all steps).

        Args:
            name: Metric name to filter by.

        Returns:
            Tuple of matching metrics in their original order.
        """
        return tuple(m for m in self.metrics if m.name == name)

    @property
    def final_metrics(self) -> tuple[ExperimentMetric, ...]:
        """Return only step-less (final scalar) metrics.

        Returns:
            Tuple of metrics with ``step == None``.
        """
        return tuple(m for m in self.metrics if m.step is None)

    @property
    def metric_names(self) -> frozenset[str]:
        """Return the set of distinct metric names in this snapshot.

        Returns:
            Frozenset of metric name strings.
        """
        return frozenset(m.name for m in self.metrics)

    def __len__(self) -> int:
        return len(self.metrics)

    def __str__(self) -> str:
        return f"MetricSnapshot({len(self.metrics)} metrics)"
