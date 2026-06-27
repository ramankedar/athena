"""Application context produced by the bootstrapper.

``ApplicationContext`` is an immutable snapshot of the platform's state
at startup completion. It is produced by ``bootstrap_application()`` and
should be passed explicitly to all engines and subsystems.

Immutability rationale:
    The context is a frozen dataclass. Any attempt to mutate a field after
    construction raises ``dataclasses.FrozenInstanceError``. This makes the
    context safe to share across threads and coroutines without defensive
    copying or synchronisation primitives.

Explicit-dependency rationale:
    The context is passed as a parameter rather than accessed via a global
    variable. This makes dependencies visible at the call site, simplifies
    testing (inject a different context), and prevents hidden coupling
    between subsystems that share the same global state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from athena.platform.config.settings import AthenaSettings
    from athena.platform.types.enums import ApplicationMode, Environment


@dataclass(frozen=True)
class ApplicationContext:
    """Immutable snapshot of platform state at startup completion.

    Produced by ``bootstrap_application()`` and passed to all engines
    at initialisation. Contains everything an engine needs to understand
    the current platform configuration without re-loading settings.

    Attributes:
        settings: Fully validated and resolved platform settings.
        started_at: UTC timestamp marking when the bootstrap completed.

    Example::

        ctx = bootstrap_application()
        log.info(
            "engine.starting",
            environment=ctx.environment.value,
            mode=ctx.mode.value,
        )
    """

    settings: AthenaSettings
    started_at: datetime

    @property
    def environment(self) -> Environment:
        """Current deployment environment.

        Returns:
            The ``Environment`` value from the resolved settings.
        """
        return self.settings.environment

    @property
    def mode(self) -> ApplicationMode:
        """Current operational mode.

        Returns:
            The ``ApplicationMode`` from ``settings.app.mode``.
        """
        return self.settings.app.mode

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in the production environment.

        Returns:
            Delegates to ``settings.is_production``.
        """
        return self.settings.is_production

    @property
    def is_development(self) -> bool:
        """Return ``True`` when running in the development environment.

        Returns:
            Delegates to ``settings.is_development``.
        """
        return self.settings.is_development

    @property
    def is_testing(self) -> bool:
        """Return ``True`` when running under the test suite.

        Returns:
            Delegates to ``settings.is_testing``.
        """
        return self.settings.is_testing
