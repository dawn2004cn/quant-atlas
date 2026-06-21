# Phase 16 — auto hot-swap patch (EvolutionArbiter)
try:
    import app.domain.alpha.auto_hotswap_patch  # noqa: F401
    logger.debug("Auto hot-swap trigger wired")
except Exception as exc:
    logger.warning("Auto hot-swap patch skipped: %s", exc)

# Phase 16 — PromptEvolutionService ↔ DecisionFeedbackService loop
try:
    import app.modules.ai_agent.services.prompt_evolution_service  # noqa: F401
    import app.application.services.decision_feedback_service  # noqa: F401
    logger.debug("Prompt <> Decision feedback loop initialized")
except Exception as exc:
    logger.warning("Feedback loop wire skipped: %s", exc)
