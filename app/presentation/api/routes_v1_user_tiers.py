"""User Tier API — dispatcher to per-tier sub-modules.

The per-tier modules (retail, boutique, investment, fund, institution)
each carry their own ``@register_routes`` decorator and are discovered
independently. This file is retained for backward compatibility with
the route preloader and for import-side-effects only.
"""

from __future__ import annotations

# Side-effect: importing the sub-package triggers @register_routes decorators
from .v1 import user_tiers  # noqa: F401
