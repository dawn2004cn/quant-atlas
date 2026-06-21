"""DEPRECATED — This module is no longer used.

All functionality has been consolidated into ``app.core.typed_registry``.

Migration guide:
    - ``@register_service`` → ``@service()`` or ``@registry.service()`` from ``app.core.typed_registry``
    - ``register_factory()`` → ``@factory()`` or ``@registry.factory()`` from ``app.core.typed_registry``
    - ``ServiceRegistry`` → ``TypedServiceRegistry`` from ``app.core.typed_registry``
    - ``configure_service_registry()`` → ``TypedServiceRegistry(config=...)`` from ``app.core.typed_registry``

Removed in:
    - ``app.core.registry`` now imports directly from ``app.core.typed_registry``

This file can be deleted after verifying no other imports reference it.
"""

# The legacy shim is intentionally empty.
