"""Auto-discovered application modules.

Each module in this package decorated with ``@module`` self-registers
its ``register_routes`` and can declare service dependencies.
"""

from app.infrastructure.modules import qlib_module, tdx_module
