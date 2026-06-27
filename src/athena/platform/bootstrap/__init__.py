"""Application bootstrap.

Re-exports the public bootstrap API::

    from athena.platform.bootstrap import bootstrap_application, ApplicationContext
"""

from athena.platform.bootstrap.bootstrapper import bootstrap_application
from athena.platform.bootstrap.context import ApplicationContext

__all__ = [
    "ApplicationContext",
    "bootstrap_application",
]
