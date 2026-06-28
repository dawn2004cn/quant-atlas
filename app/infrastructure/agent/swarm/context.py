from __future__ import annotations
"""ContextBuilder: builds LLM message context for the ReAct AgentLoop.

Ported from Vibe-Trading.
"""


import json
from datetime import datetime
from typing import Any

from app.infrastructure.agent.swarm.workspace_memory import WorkspaceMemory
from app.infrastructure.agent.skills.loader import SkillsLoader
from app.infrastructure.agent.swarm.tools_base import ToolRegistry
from app.infrastructure.agent.memory.persistent import PersistentMemory
from app.infrastructure.agent.memory.vector.store import VectorMemoryStore


from app.core.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a finance research agent with {skill_count} specialist skills, {tool_count} tools, 5 data sources (with auto-fallback), and 29 multi-agent swarm teams.
You handle backtesting, factor analysis, options pricing, risk audits, research reports, document/web reading, web search, and team-based workflows.

## Tools

{tool_descriptions}

## Skills (use load_skill to read full docs)

{skill_descriptions}

## State

{memory_summary}

## Task Routing

Decide which workflow to use based on the request:

**Backtest** — user wants to create, test, or optimize a trading strategy:
1. `load_skill("strategy-generate")` — read the SignalEngine contract
2. `write_file("config.json", ...)` — source, codes, dates, parameters
3. `write_file("code/signal_engine.py", ...)` — SignalEngine class
4. Syntax check → `backtest(run_dir=...)` → `read_file("artifacts/metrics.csv")`
5. Do NOT write run_backtest.py. The engine is built-in.

**Swarm team** — ONLY when the user explicitly requests team/committee/swarm analysis:
- Call `run_swarm(prompt="<user's full request>")` — it auto-selects the right preset.
- Do NOT use swarm unless the user specifically asks for team-based or committee analysis.

**Analysis / research** — user wants factor analysis, options pricing, market data, or general research:
- Load the relevant skill first, then use the matching tool (factor_analysis, options_pricing, bash for custom scripts).

**Document / web** — user provides a PDF or URL:
- `read_document(path=...)` for PDFs, `read_url(url=...)` for web pages.

**Trade journal** — user uploads a CSV/Excel broker export (交割单) or asks to analyze their own trading history:
1. `load_skill("trade-journal")` — read analysis methodology and report templates
2. `analyze_trade_journal(file_path=..., analysis_type="full")` — parse + profile + behavior diagnostics
3. Present results as the markdown report in the skill. Offer follow-ups: time-slice, symbol deep-dive, market split.
4. If the user asks "now what / can I do better / what if I had discipline", switch to the **Shadow Account** flow below.

**Shadow Account** — user asks to extract their strategy, "train a shadow", multi-market backtest their own profitable pattern, or ask "how much am I leaving on the table":
1. **MUST** `load_skill("shadow-account")` as the FIRST tool call before any shadow_* tool — the skill defines rules, methodology, attribution semantics, and is required context
2. Confirm the journal has been parsed (same session or known `journal_path`). If not, run `analyze_trade_journal` first.
3. `extract_shadow_strategy(journal_path=...)` → show rules, ask user to confirm they look like their own behavior
4. `run_shadow_backtest(shadow_id=..., journal_path=...)` → multi-market metrics + delta attribution
5. `render_shadow_report(shadow_id=...)` → share html/pdf path, lead with the Section 5 "you vs shadow" delta
6. Optional: `scan_shadow_signals(shadow_id=...)` on request (always attach the research-only disclaimer)
**Never** call `extract_shadow_strategy` / `run_shadow_backtest` / `render_shadow_report` / `scan_shadow_signals` without first loading the `shadow-account` skill in the same session.

## Guidelines

- Load the relevant skill BEFORE starting any task. Skills contain the exact API contracts and examples.
- **Continuous Learning:** When you develop a highly effective research workflow, a new factor analysis pattern, or a robust data processing script, use `save_skill` to archive it. Give it a descriptive name and clear documentation. This makes your successful work reusable for future Swarm agents.
- Ask the user if critical info is missing (assets, dates, strategy type). Never guess.
- Output results as markdown tables. After backtest, always report: total_return, sharpe, max_drawdown, trade_count.
- All file paths are relative to run_dir (auto-injected).
- Respond in the same language the user used.
- You have persistent cross-session memory (`remember` tool). When the user shares preferences, strategy insights, or important findings, save them for future sessions.
- You can create reusable skills (`save_skill`) when a workflow succeeds, and fix them (`patch_skill`) when APIs change.
{memory_section}
## Current Date & Time

Today is {current_datetime}.
"""

_MEMORY_SECTION = """
## Persistent Memory (cross-session)

{snapshot}

"""


class ContextBuilder:
    """Builds message context for AgentLoop."""

    def __init__(self, registry: ToolRegistry, memory: WorkspaceMemory,
                 skills_loader: SkillsLoader | None = None,
                 persistent_memory: PersistentMemory | None = None,
                 vector_memory: VectorMemoryStore | None = None) -> None:
        self.registry = registry
        self.memory = memory
        self.skills_loader = skills_loader or SkillsLoader()
        self._persistent_memory = persistent_memory
        self._vector_memory = vector_memory

    def build_system_prompt(self, user_message: str = "") -> str:
        now = datetime.now()

        memory_section = ""
        if self._persistent_memory and self._persistent_memory.snapshot:
            memory_section = _MEMORY_SECTION.format(
                snapshot=self._persistent_memory.snapshot,
            )

        return _SYSTEM_PROMPT.format(
            tool_count=len(self.registry._tools),
            skill_count=len(self.skills_loader.skills),
            tool_descriptions=self._format_tool_descriptions(),
            skill_descriptions=self.skills_loader.get_descriptions(),
            memory_summary=self.memory.to_summary(),
            memory_section=memory_section,
            current_datetime=now.strftime("%A, %B %d, %Y %H:%M (local)"),
        )

    def build_messages(self, user_message: str, history: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.build_system_prompt(user_message)},
        ]
        if history:
            messages.extend(history)

        # Context enrichment with persistent and semantic memory
        enriched = user_message
        context_sources = []

        if self._persistent_memory:
            try:
                recalls = self._persistent_memory.find_relevant(user_message, max_results=3)
                if recalls:
                    context_sources.append("--- Persistent Memory Recalls ---\n" +
                                         "\n".join([f"- **{r.title}** ({r.memory_type}): {r.body[:500]}" for r in recalls]))
            except Exception as exc:
                logger.debug("Auto-recall failed: %s", exc)

        if self._vector_memory:
            try:
                semantic = self._vector_memory.retrieve_context(user_message)
                if semantic and "No relevant" not in semantic:
                    context_sources.append("--- Semantic Knowledge Graph ---\n" + semantic)
            except Exception as exc:
                logger.debug("Vector memory recall failed: %s", exc)

        if context_sources:
            enriched = f"<context>\n{chr(10).join(context_sources)}\n</context>\n\n{user_message}"

        messages.append({"role": "user", "content": enriched})
        return messages

    def _format_tool_descriptions(self) -> str:
        lines = []
        for tool in self.registry._tools.values():
            params = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            param_parts = []
            for pname, pschema in params.items():
                req = " (required)" if pname in required else ""
                param_parts.append(f"    - {pname}: {pschema.get('description', pschema.get('type', ''))}{req}")
            param_text = "\n".join(param_parts) if param_parts else "    (no params)"
            lines.append(f"### {tool.name}\n{tool.description}\n  Params:\n{param_text}")
        return "\n\n".join(lines)

    @staticmethod
    def format_tool_result(tool_call_id: str, tool_name: str, result: str) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
        }

    @staticmethod
    def format_assistant_tool_calls(
        tool_calls: list,
        content: str | None = None,
        reasoning_content: str | None = None,
    ) -> dict[str, Any]:
        message = {
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in tool_calls
            ],
        }
        if reasoning_content is not None:
            message["reasoning_content"] = reasoning_content
        return message
