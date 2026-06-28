"""Unit tests for experiment metric value objects."""

from __future__ import annotations

import pytest

from athena.experiments.exceptions import InvalidExperimentError
from athena.experiments.metrics import ExperimentMetric, MetricDirection, MetricSnapshot


class TestMetricDirection:
    def test_values(self) -> None:
        assert MetricDirection.HIGHER_IS_BETTER == "higher_is_better"
        assert MetricDirection.LOWER_IS_BETTER == "lower_is_better"
        assert MetricDirection.NEUTRAL == "neutral"


class TestExperimentMetric:
    def test_valid_scalar(self) -> None:
        m = ExperimentMetric("sharpe_ratio", 1.5, MetricDirection.HIGHER_IS_BETTER)
        assert m.value == 1.5
        assert m.direction == MetricDirection.HIGHER_IS_BETTER

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="name"):
            ExperimentMetric("", 1.0)

    def test_negative_step_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="step"):
            ExperimentMetric("loss", 0.5, step=-1)

    def test_invalid_confidence_interval_raises(self) -> None:
        with pytest.raises(InvalidExperimentError, match="confidence"):
            ExperimentMetric("sharpe", 1.0, confidence_lower=0.5, confidence_upper=0.3)

    def test_comparison_value_higher_is_better(self) -> None:
        m = ExperimentMetric("sharpe", 2.0, MetricDirection.HIGHER_IS_BETTER)
        assert m.comparison_value == 2.0

    def test_comparison_value_lower_is_better(self) -> None:
        m = ExperimentMetric("drawdown", -30.0, MetricDirection.LOWER_IS_BETTER)
        assert m.comparison_value == 30.0  # negated

    def test_comparison_value_neutral(self) -> None:
        m = ExperimentMetric("regime", 1.0, MetricDirection.NEUTRAL)
        assert m.comparison_value == 1.0

    def test_has_confidence_interval_true(self) -> None:
        m = ExperimentMetric("sharpe", 1.5, confidence_lower=1.0, confidence_upper=2.0)
        assert m.has_confidence_interval is True

    def test_has_confidence_interval_false(self) -> None:
        m = ExperimentMetric("sharpe", 1.5)
        assert m.has_confidence_interval is False

    def test_is_better_than_higher(self) -> None:
        m1 = ExperimentMetric("sharpe", 2.0, MetricDirection.HIGHER_IS_BETTER)
        m2 = ExperimentMetric("sharpe", 1.0, MetricDirection.HIGHER_IS_BETTER)
        assert m1.is_better_than(m2) is True
        assert m2.is_better_than(m1) is False

    def test_is_better_than_lower(self) -> None:
        # For LOWER_IS_BETTER, report drawdown as a positive percentage.
        # 10% drawdown (smaller loss) is better than 30% drawdown.
        m1 = ExperimentMetric("max_drawdown_pct", 10.0, MetricDirection.LOWER_IS_BETTER)
        m2 = ExperimentMetric("max_drawdown_pct", 30.0, MetricDirection.LOWER_IS_BETTER)
        assert m1.is_better_than(m2) is True  # 10% < 30%, lower is better

    def test_is_better_than_different_names_raises(self) -> None:
        m1 = ExperimentMetric("sharpe", 2.0, MetricDirection.HIGHER_IS_BETTER)
        m2 = ExperimentMetric("sortino", 1.0, MetricDirection.HIGHER_IS_BETTER)
        with pytest.raises(InvalidExperimentError, match="different names"):
            m1.is_better_than(m2)

    def test_is_better_than_different_directions_raises(self) -> None:
        m1 = ExperimentMetric("x", 2.0, MetricDirection.HIGHER_IS_BETTER)
        m2 = ExperimentMetric("x", 1.0, MetricDirection.LOWER_IS_BETTER)
        with pytest.raises(InvalidExperimentError, match="directions"):
            m1.is_better_than(m2)

    def test_str(self) -> None:
        m = ExperimentMetric("sharpe_ratio", 1.5, MetricDirection.HIGHER_IS_BETTER)
        s = str(m)
        assert "sharpe_ratio" in s
        assert "1.5" in s

    def test_iterative_metric_with_step(self) -> None:
        m = ExperimentMetric("loss", 0.5, step=10)
        assert m.step == 10
        assert "step=10" in str(m)


class TestMetricSnapshot:
    def test_empty(self) -> None:
        snap = MetricSnapshot.empty()
        assert len(snap) == 0

    def test_get_found(self) -> None:
        m = ExperimentMetric("sharpe", 1.5)
        snap = MetricSnapshot(metrics=(m,))
        result = snap.get("sharpe")
        assert result is m

    def test_get_not_found(self) -> None:
        snap = MetricSnapshot.empty()
        assert snap.get("nonexistent") is None

    def test_get_with_step(self) -> None:
        m = ExperimentMetric("loss", 0.5, step=5)
        snap = MetricSnapshot(metrics=(m,))
        assert snap.get("loss", step=5) is m
        assert snap.get("loss", step=10) is None

    def test_duplicate_name_step_raises(self) -> None:
        m = ExperimentMetric("sharpe", 1.5)
        with pytest.raises(InvalidExperimentError, match="Duplicate"):
            MetricSnapshot(metrics=(m, m))

    def test_all_named(self) -> None:
        m1 = ExperimentMetric("loss", 0.5, step=1)
        m2 = ExperimentMetric("loss", 0.3, step=2)
        m3 = ExperimentMetric("sharpe", 1.5)
        snap = MetricSnapshot(metrics=(m1, m2, m3))
        loss_metrics = snap.all_named("loss")
        assert len(loss_metrics) == 2

    def test_final_metrics(self) -> None:
        m1 = ExperimentMetric("sharpe", 1.5)
        m2 = ExperimentMetric("loss", 0.5, step=1)
        snap = MetricSnapshot(metrics=(m1, m2))
        finals = snap.final_metrics
        assert len(finals) == 1
        assert finals[0].name == "sharpe"

    def test_metric_names(self) -> None:
        m1 = ExperimentMetric("sharpe", 1.5)
        m2 = ExperimentMetric("loss", 0.5, step=1)
        snap = MetricSnapshot(metrics=(m1, m2))
        assert snap.metric_names == frozenset({"sharpe", "loss"})

    def test_str(self) -> None:
        snap = MetricSnapshot.empty()
        assert "0 metrics" in str(snap)
