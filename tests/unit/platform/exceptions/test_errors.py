"""Unit tests for the platform exception hierarchy."""

from __future__ import annotations

import pytest

from athena.platform.exceptions.errors import (
    AthenaError,
    ConfigurationError,
    DataIntegrityError,
    ExternalServiceError,
    InfrastructureError,
    NotImplementedFeatureError,
    ValidationError,
)


class TestAthenaError:
    def test_is_exception(self) -> None:
        assert issubclass(AthenaError, Exception)

    def test_message_stored(self) -> None:
        exc = AthenaError("something failed")
        assert exc.message == "something failed"

    def test_message_is_args(self) -> None:
        exc = AthenaError("something failed")
        assert str(exc) == "something failed"

    def test_error_code_none_by_default(self) -> None:
        exc = AthenaError("msg")
        assert exc.error_code is None

    def test_error_code_stored(self) -> None:
        exc = AthenaError("msg", error_code="ATH_001")
        assert exc.error_code == "ATH_001"

    def test_empty_context_by_default(self) -> None:
        exc = AthenaError("msg")
        assert exc.context == {}

    def test_context_kwargs_stored(self) -> None:
        exc = AthenaError("msg", component="data", symbol="NSE:NIFTY50-INDEX")
        assert exc.context == {"component": "data", "symbol": "NSE:NIFTY50-INDEX"}

    def test_context_accepts_mixed_value_types(self) -> None:
        exc = AthenaError("msg", count=42, flag=True, ratio=0.5, name="x", nothing=None)
        assert exc.context["count"] == 42
        assert exc.context["flag"] is True
        assert exc.context["ratio"] == 0.5
        assert exc.context["name"] == "x"
        assert exc.context["nothing"] is None

    def test_to_dict_structure(self) -> None:
        exc = AthenaError("msg", error_code="ATH_001", component="data")
        result = exc.to_dict()
        assert result["error_type"] == "AthenaError"
        assert result["message"] == "msg"
        assert result["error_code"] == "ATH_001"
        assert result["context"] == {"component": "data"}

    def test_to_dict_with_none_error_code(self) -> None:
        exc = AthenaError("msg")
        assert exc.to_dict()["error_code"] is None

    def test_repr_minimal(self) -> None:
        exc = AthenaError("bad thing")
        assert repr(exc) == "AthenaError('bad thing')"

    def test_repr_with_error_code(self) -> None:
        exc = AthenaError("bad thing", error_code="ATH_001")
        assert "ATH_001" in repr(exc)
        assert "error_code" in repr(exc)

    def test_repr_with_context(self) -> None:
        exc = AthenaError("bad", component="data")
        assert "component" in repr(exc)
        assert "data" in repr(exc)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(AthenaError) as exc_info:
            raise AthenaError("test error", error_code="T_001", key="val")
        assert exc_info.value.error_code == "T_001"
        assert exc_info.value.context["key"] == "val"


class TestConfigurationError:
    def test_is_athena_error(self) -> None:
        assert issubclass(ConfigurationError, AthenaError)

    def test_is_exception(self) -> None:
        assert issubclass(ConfigurationError, Exception)

    def test_caught_as_athena_error(self) -> None:
        with pytest.raises(AthenaError):
            raise ConfigurationError("bad config", error_code="CFG_001")

    def test_context_preserved(self) -> None:
        exc = ConfigurationError("bad", missing_key="ATHENA_X")
        assert exc.context["missing_key"] == "ATHENA_X"


class TestValidationError:
    def test_is_athena_error(self) -> None:
        assert issubclass(ValidationError, AthenaError)

    def test_caught_as_athena_error(self) -> None:
        with pytest.raises(AthenaError):
            raise ValidationError("invalid symbol", field="symbol", value="??")

    def test_not_configuration_error(self) -> None:
        assert not issubclass(ValidationError, ConfigurationError)


class TestInfrastructureError:
    def test_is_athena_error(self) -> None:
        assert issubclass(InfrastructureError, AthenaError)

    def test_caught_as_athena_error(self) -> None:
        with pytest.raises(AthenaError):
            raise InfrastructureError("DB unavailable", component="timescaledb")


class TestExternalServiceError:
    def test_is_infrastructure_error(self) -> None:
        assert issubclass(ExternalServiceError, InfrastructureError)

    def test_is_athena_error(self) -> None:
        assert issubclass(ExternalServiceError, AthenaError)

    def test_caught_as_infrastructure_error(self) -> None:
        with pytest.raises(InfrastructureError):
            raise ExternalServiceError("Fyers API timeout", service="fyers", status=504)

    def test_caught_as_athena_error(self) -> None:
        with pytest.raises(AthenaError):
            raise ExternalServiceError("Fyers API timeout")


class TestDataIntegrityError:
    def test_is_athena_error(self) -> None:
        assert issubclass(DataIntegrityError, AthenaError)

    def test_not_infrastructure_error(self) -> None:
        assert not issubclass(DataIntegrityError, InfrastructureError)

    def test_caught_as_athena_error(self) -> None:
        with pytest.raises(AthenaError):
            raise DataIntegrityError("audit hash mismatch", sequence=42)


class TestNotImplementedFeatureError:
    def test_is_athena_error(self) -> None:
        assert issubclass(NotImplementedFeatureError, AthenaError)

    def test_message_includes_feature_name(self) -> None:
        exc = NotImplementedFeatureError("ML signal scoring")
        assert "ML signal scoring" in str(exc)
        assert "not yet implemented" in str(exc)

    def test_feature_stored(self) -> None:
        exc = NotImplementedFeatureError("feature X")
        assert exc.feature == "feature X"

    def test_feature_in_context(self) -> None:
        exc = NotImplementedFeatureError("feature X")
        assert exc.context["feature"] == "feature X"

    def test_planned_sprint_none_by_default(self) -> None:
        exc = NotImplementedFeatureError("feature X")
        assert exc.planned_sprint is None

    def test_planned_sprint_stored(self) -> None:
        exc = NotImplementedFeatureError("feature X", planned_sprint="sprint-5")
        assert exc.planned_sprint == "sprint-5"

    def test_planned_sprint_in_context(self) -> None:
        exc = NotImplementedFeatureError("feature X", planned_sprint="sprint-5")
        assert exc.context["planned_sprint"] == "sprint-5"

    def test_planned_sprint_absent_from_context_when_none(self) -> None:
        exc = NotImplementedFeatureError("feature X")
        assert "planned_sprint" not in exc.context

    def test_extra_context_stored(self) -> None:
        exc = NotImplementedFeatureError("feat", engine="intelligence")
        assert exc.context["engine"] == "intelligence"

    def test_error_code_stored(self) -> None:
        exc = NotImplementedFeatureError("feat", error_code="NIF_001")
        assert exc.error_code == "NIF_001"

    def test_caught_as_athena_error(self) -> None:
        with pytest.raises(AthenaError):
            raise NotImplementedFeatureError("ML")
