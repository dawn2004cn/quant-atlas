"""Shared repository wiring: factory, deps, facades, registration."""
# Registration is NOT auto-triggered here to avoid circular imports.
# Call ensure_registered() explicitly before using the factory.
