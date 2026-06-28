"""Patch for OpenBB Platform 4.x dynamic interface issues."""

import openbb_core.app.provider_interface as pi

from app.core.logger import get_logger

logger = get_logger(__name__)

def apply_openbb_patch():
    """Apply monkeypatch to openbb_core.app.provider_interface to resolve dynamic OBBject models."""
    if hasattr(pi, "__getattr__"):
        # Already patched or has a handler
        return

    original_getattr = getattr(pi, "__getattr__", None)

    def __getattr__(name):
        if name.startswith("OBBject_"):
            try:
                # Try to get it from the Singleton instance
                from openbb_core.app.provider_interface import ProviderInterface
                interface = ProviderInterface()
                # return_annotations contains the dynamically created OBBject_ models
                model_name = name[8:] # strip "OBBject_"
                if model_name in interface.return_annotations:
                    return interface.return_annotations[model_name]
            except Exception as e:
                logger.debug(f"Failed to resolve dynamic OpenBB model {name}: {e}")

        if original_getattr:
            return original_getattr(name)
        raise AttributeError(f"module {pi.__name__} has no attribute {name}")

    pi.__getattr__ = __getattr__
    logger.info("Applied dynamic attribute patch to openbb_core.app.provider_interface")

# Auto-apply when imported
apply_openbb_patch()
