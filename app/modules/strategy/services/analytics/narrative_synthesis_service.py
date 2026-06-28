from __future__ import annotations

"""Narrative Synthesis Layer — generative, personalized research briefings (7.0)."""

import json
import re
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_SUCCESS_OUTCOMES = frozenset({"win", "profit", "success", "correct", "bullish", "positive"})


class NarrativeSynthesisService:
    """Turn structured briefing facts into causal, user-aware narratives."""

    def __init__(
        self,
        *,
        user_knowledge_service: Any | None = None,
        user_decision_context_service: Any | None = None,
        sequence_chain_service: Any | None = None,
    ) -> None:
        self._knowledge = user_knowledge_service
        self._decision = user_decision_context_service
        self._sequence_chain = sequence_chain_service

    def synthesize_daily_briefing(
        self,
        *,
        user_id: str | int,
        briefing: dict[str, Any],
        investment_profile: dict[str, Any] | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Augment raw briefing with narrative fields."""
        knowledge: dict[str, Any] = {}
        if self._knowledge is not None:
            try:
                knowledge = self._knowledge.build_context_enrichment(user_id)
                profile = self._knowledge.get_profile(user_id)
                patterns = profile.get("decision_patterns") or []
                if patterns and not knowledge.get("related_decision_patterns"):
                    knowledge["related_decision_patterns"] = patterns[-10:]
                knowledge["behavior_topology"] = self._knowledge.analyze_topology(user_id)
            except Exception as exc:
                logger.debug("narrative knowledge enrichment: %s", exc)

        decision_ctx: dict[str, Any] = {}
        if self._decision is not None:
            try:
                decision_ctx = self._decision.build_context(
                    user_id=user_id,
                    role=role,
                    investment_profile=investment_profile,
                    page="smart_briefing",
                )
            except Exception as exc:
                logger.debug("narrative decision context: %s", exc)

        evidence_nodes = self._collect_evidence_nodes(briefing)
        success_patterns = self._success_patterns(knowledge)
        fallback = self._template_narrative(
            briefing, knowledge, success_patterns, decision_ctx, evidence_nodes
        )
        llm_result = self._llm_narrative(
            briefing, knowledge, decision_ctx, success_patterns, evidence_nodes, user_id=user_id
        )

        narrative_level = (decision_ctx.get("dto_directives") or {}).get("narrative_level") or "normal"
        if llm_result:
            out = {
                "mode": "llm",
                "opening": llm_result.get("opening") or fallback["opening"],
                "market_narrative": llm_result.get("market_narrative") or fallback["market_narrative"],
                "recommendation_narratives": self._merge_rec_narratives(
                    briefing, llm_result.get("recommendation_narratives"), fallback
                ),
                "personalized_closing": llm_result.get("personalized_closing")
                or fallback["personalized_closing"],
                "causal_hooks": llm_result.get("causal_hooks") or fallback.get("causal_hooks", []),
                "evidence_nodes": evidence_nodes,
            }
        else:
            out = {**fallback, "mode": "template", "evidence_nodes": evidence_nodes}

        if narrative_level == "full":
            causal = self.synthesize_causal_report(
                user_id=user_id,
                briefing=briefing,
                investment_profile=investment_profile,
                role=role,
            )
            if causal.get("report_markdown"):
                out["causal_report"] = causal
        return out

    def synthesize_causal_report(
        self,
        *,
        user_id: str | int,
        symbol: str | None = None,
        briefing: dict[str, Any] | None = None,
        investment_profile: dict[str, Any] | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Narrative 2.0 — long-form causal research report from SequenceChain evidence."""
        briefing = briefing or {}
        symbols = []
        if symbol:
            symbols.append(str(symbol).strip().lower())
        for rec in briefing.get("recommendations") or []:
            sym = str(rec.get("symbol") or "").strip().lower()
            if sym and sym not in symbols:
                symbols.append(sym)
        if not symbols:
            symbols = ["600519"]

        knowledge: dict[str, Any] = {}
        if self._knowledge is not None:
            try:
                knowledge = self._knowledge.build_context_enrichment(user_id)
            except Exception as exc:
                logger.debug("causal report knowledge: %s", exc)

        decision_ctx: dict[str, Any] = {}
        if self._decision is not None:
            try:
                decision_ctx = self._decision.build_context(
                    user_id=user_id,
                    role=role,
                    investment_profile=investment_profile,
                    page="causal_report",
                )
            except Exception as exc:
                logger.debug("causal report decision ctx: %s", exc)

        chain_context = self._collect_full_chain_context(symbols)
        structured_narrative = self._structure_chain_narrative(chain_context)
        evidence_chains = self._extract_evidence_chains(chain_context)
        template_report = self._template_causal_report(symbols, chain_context, briefing, structured_narrative)
        llm_report = self._llm_causal_report(
            symbols=symbols,
            briefing=briefing,
            knowledge=knowledge,
            decision_ctx=decision_ctx,
            chain_context=chain_context,
            structured_narrative=structured_narrative,
            user_id=user_id,
        )
        if llm_report:
            return {
                "mode": "llm",
                "symbols": symbols,
                "report_markdown": llm_report.get("report_markdown") or template_report["report_markdown"],
                "sections": llm_report.get("sections") or template_report["sections"],
                "chain_steps": len(chain_context),
                "chain_summary": structured_narrative.get("summary", ""),
                "confidence": float(llm_report.get("confidence") or 0.82),
                "evidence_chains": evidence_chains,
            }
        return {
            **template_report,
            "mode": "template",
            "symbols": symbols,
            "chain_steps": len(chain_context),
            "chain_summary": structured_narrative.get("summary", ""),
            "evidence_chains": evidence_chains,
        }

    def _collect_full_chain_context(self, symbols: list[str]) -> list[dict[str, Any]]:
        """Serialize complete SequenceChain steps for narrative 2.0."""
        if self._sequence_chain is None:
            return []
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for sym in symbols[:5]:
            try:
                chains = self._sequence_chain.list_chains(symbol=sym, limit=3)
            except Exception as exc:
                logger.debug("causal chain list: %s", exc)
                continue
            for chain in chains:
                if chain.provenance_id in seen:
                    continue
                seen.add(chain.provenance_id)
                for step in chain.steps:
                    rows.append(
                        {
                            "symbol": chain.symbol,
                            "provenance_id": chain.provenance_id,
                            "status": chain.status,
                            "step_id": step.step_id,
                            "event_type": step.event_type,
                            "label": step.label,
                            "timestamp": step.timestamp,
                            "payload": step.payload,
                        }
                    )
        return rows[:60]

    def _structure_chain_narrative(self, chain_context: list[dict[str, Any]]) -> dict[str, Any]:
        """Group chain steps by provenance_id and create causal flow summaries."""
        if not chain_context:
            return {"chains": [], "summary": ""}

        by_prov: dict[str, list[dict[str, Any]]] = {}
        for step in chain_context:
            prov = step.get("provenance_id") or "unknown"
            by_prov.setdefault(prov, []).append(step)

        chains: list[dict[str, Any]] = []
        for prov_id, steps in by_prov.items():
            steps_sorted = sorted(steps, key=lambda s: s.get("timestamp") or "")
            symbol = steps_sorted[0].get("symbol", "")
            status = steps_sorted[0].get("status", "")

            debate_steps = [s for s in steps_sorted if s.get("event_type") == "DebateRoundEvent"]
            consensus_steps = [s for s in steps_sorted if s.get("event_type") == "ArbiterConsensusEvent"]
            correction_steps = [s for s in steps_sorted if s.get("event_type") == "CorrectionIntentEvent"]
            trade_steps = [s for s in steps_sorted if s.get("event_type") == "TradeExecutedEvent"]

            debate_summary = []
            for d in debate_steps:
                payload = d.get("payload") or {}
                role = payload.get("agent_role") or d.get("label", "")
                stance = payload.get("stance") or ""
                evidence = payload.get("evidence_summary") or ""
                confidence = payload.get("confidence") or 0
                debate_summary.append({
                    "role": role,
                    "stance": stance,
                    "evidence": evidence[:200] if evidence else "",
                    "confidence": confidence,
                })

            consensus_info = None
            if consensus_steps:
                c = consensus_steps[-1]
                payload = c.get("payload") or {}
                consensus_info = {
                    "verdict": payload.get("verdict") or c.get("label", ""),
                    "confidence": payload.get("confidence") or 0,
                    "mode": payload.get("mode") or "",
                }

            corrections = []
            for corr in correction_steps:
                payload = corr.get("payload") or {}
                corrections.append({
                    "change_type": payload.get("change_type") or "",
                    "rationale": payload.get("rationale") or "",
                    "prior_verdict": payload.get("prior_verdict") or "",
                    "new_verdict": payload.get("new_verdict") or "",
                })

            trade_info = None
            if trade_steps:
                t = trade_steps[-1]
                payload = t.get("payload") or {}
                trade_info = {
                    "action": payload.get("action") or "",
                    "side": payload.get("side") or "",
                    "quantity": payload.get("quantity") or 0,
                }

            causal_flow = self._build_causal_flow(debate_summary, consensus_info, corrections, trade_info)

            chains.append({
                "provenance_id": prov_id,
                "symbol": symbol,
                "status": status,
                "step_count": len(steps_sorted),
                "debate_rounds": len(debate_steps),
                "debate_summary": debate_summary,
                "consensus": consensus_info,
                "corrections": corrections,
                "trade": trade_info,
                "causal_flow": causal_flow,
            })

        summary = self._build_chain_summary(chains)
        return {"chains": chains, "summary": summary}

    @staticmethod
    def _build_causal_flow(
        debate: list[dict],
        consensus: dict | None,
        corrections: list[dict],
        trade: dict | None,
    ) -> str:
        """Build a human-readable causal flow narrative."""
        parts = []
        if debate:
            bulls = [d for d in debate if d.get("stance", "").lower() in ("bullish", "bull")]
            bears = [d for d in debate if d.get("stance", "").lower() in ("bearish", "bear")]
            if bulls:
                parts.append(f"多头方({len(bulls)}轮)提出: {bulls[0].get('evidence', '')[:80]}")
            if bears:
                parts.append(f"空头方({len(bears)}轮)反驳: {bears[0].get('evidence', '')[:80]}")

        if consensus:
            verdict = consensus.get("verdict", "")
            conf = consensus.get("confidence", 0)
            parts.append(f"仲裁结论: {verdict}(置信度{conf:.0%})")

        if corrections:
            for c in corrections:
                parts.append(f"修正({c.get('change_type', '')}): {c.get('rationale', '')[:60]}")

        if trade:
            parts.append(f"执行交易: {trade.get('action', '')} {trade.get('side', '')}")

        return " → ".join(parts) if parts else "无因果链数据"

    @staticmethod
    def _build_chain_summary(chains: list[dict[str, Any]]) -> str:
        """Build overall summary of all chains."""
        if not chains:
            return "无 SequenceChain 数据"

        total_debates = sum(c.get("debate_rounds", 0) for c in chains)
        symbols = list({c.get("symbol", "") for c in chains if c.get("symbol")})
        consensus_count = sum(1 for c in chains if c.get("consensus"))

        parts = [f"共 {len(chains)} 条因果链"]
        if symbols:
            parts.append(f"覆盖标的: {', '.join(symbols[:3])}")
        parts.append(f"累计辩论 {total_debates} 轮")
        if consensus_count:
            parts.append(f"{consensus_count} 条达成仲裁共识")

        return "，".join(parts) + "。"

    def _extract_evidence_chains(self, chain_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract causal evidence chains: debate → consensus → correction → trade."""
        if not chain_context:
            return []

        by_prov: dict[str, list[dict[str, Any]]] = {}
        for step in chain_context:
            prov = step.get("provenance_id") or "unknown"
            by_prov.setdefault(prov, []).append(step)

        evidence_chains: list[dict[str, Any]] = []
        for prov_id, steps in by_prov.items():
            steps_sorted = sorted(steps, key=lambda s: s.get("timestamp") or "")
            symbol = steps_sorted[0].get("symbol", "")

            chain_events: list[dict[str, Any]] = []
            for s in steps_sorted:
                event_type = s.get("event_type", "")
                payload = s.get("payload") or {}
                chain_events.append({
                    "event_type": event_type,
                    "label": s.get("label", ""),
                    "timestamp": s.get("timestamp", ""),
                    "agent_role": payload.get("agent_role", ""),
                    "stance": payload.get("stance", ""),
                    "evidence": (payload.get("evidence_summary") or "")[:150],
                    "confidence": payload.get("confidence", 0),
                    "verdict": payload.get("verdict", ""),
                })

            if chain_events:
                evidence_chains.append({
                    "provenance_id": prov_id,
                    "symbol": symbol,
                    "events": chain_events,
                    "event_count": len(chain_events),
                })

        return evidence_chains

    def _collect_evidence_nodes(self, briefing: dict[str, Any]) -> list[dict[str, Any]]:
        """Gather recent SequenceChain steps for recommendation symbols."""
        if self._sequence_chain is None:
            return []
        recs = briefing.get("recommendations") or []
        symbols = [
            str(r.get("symbol") or "").strip().lower()
            for r in recs
            if str(r.get("symbol") or "").strip()
        ]
        if not symbols:
            return []

        nodes: list[dict[str, Any]] = []
        seen_prov: set[str] = set()
        payload_keys = (
            "evidence_summary",
            "verdict",
            "stance",
            "agent_role",
            "confidence",
            "success",
            "round_num",
            "mode",
        )
        for sym in symbols[:5]:
            try:
                chains = self._sequence_chain.list_chains(symbol=sym, limit=2)
            except Exception as exc:
                logger.debug("narrative sequence chain list: %s", exc)
                continue
            for chain in chains:
                if chain.provenance_id in seen_prov:
                    continue
                seen_prov.add(chain.provenance_id)
                for step in chain.steps[-8:]:
                    nodes.append(
                        {
                            "symbol": chain.symbol,
                            "provenance_id": chain.provenance_id,
                            "event_type": step.event_type,
                            "label": step.label,
                            "payload": {
                                k: step.payload.get(k)
                                for k in payload_keys
                                if step.payload.get(k) is not None
                            },
                        }
                    )
                if len(nodes) >= 20:
                    return nodes[:20]
        return nodes[:20]

    def _llm_narrative(
        self,
        briefing: dict[str, Any],
        knowledge: dict[str, Any],
        decision_ctx: dict[str, Any],
        success_patterns: list[dict[str, Any]],
        evidence_nodes: list[dict[str, Any]],
        user_id: int | str = 0,
    ) -> dict[str, Any] | None:
        try:
            from app.core.llm_config import get_llm_for_user

            llm = get_llm_for_user(int(user_id))
        except Exception as exc:
            logger.debug("narrative llm unavailable: %s", exc)
            return None

        recs = briefing.get("recommendations") or []
        market_env = briefing.get("market_environment") or {}
        narrative_level = (
            (decision_ctx.get("dto_directives") or {}).get("narrative_level") or "normal"
        )
        prompt = self._build_prompt(
            recs=recs,
            market_env=market_env,
            knowledge=knowledge,
            decision_ctx=decision_ctx,
            success_patterns=success_patterns,
            evidence_nodes=evidence_nodes,
            narrative_level=narrative_level,
        )
        try:
            response = llm.invoke(prompt)
            text = str(getattr(response, "content", response) or "")
            parsed = self._parse_json_block(text)
            if parsed:
                return parsed
        except Exception as exc:
            logger.warning("narrative LLM synthesis failed: %s", exc)
        return None

    def _template_narrative(
        self,
        briefing: dict[str, Any],
        knowledge: dict[str, Any],
        success_patterns: list[dict[str, Any]],
        decision_ctx: dict[str, Any],
        evidence_nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        recs = briefing.get("recommendations") or []
        market_env = briefing.get("market_environment") or {}
        regime_desc = market_env.get("regime_description") or "市场环境中性"
        top_symbols = [s.get("id") for s in knowledge.get("top_symbols") or [] if s.get("id")]
        frequent = (decision_ctx.get("decision_history") or {}).get("frequent_symbols") or []

        opening = f"早安，今日操盘环境：{regime_desc}。"
        if top_symbols:
            opening += f" 您近期重点关注 {', '.join(top_symbols[:3])}。"

        causal_hooks: list[str] = []
        if success_patterns:
            pat = success_patterns[0]
            syms = pat.get("symbols") or []
            if syms:
                causal_hooks.append(
                    f"您曾在 {syms[0]} 上的成功{'抄底' if 'reversal' in str(pat.get('outcome')) else '交易'}模式值得复用"
                )
        for node in evidence_nodes:
            if node.get("event_type") != "ArbiterConsensusEvent":
                continue
            verdict = (node.get("payload") or {}).get("verdict") or node.get("label", "")
            sym = node.get("symbol") or ""
            causal_hooks.append(f"系统仲裁链对 {sym} 给出 {verdict} 结论，与今日推荐逻辑一致。")
            break

        rec_narratives = []
        for rec in recs:
            sym = rec.get("symbol") or ""
            name = rec.get("name") or sym
            reasons = rec.get("reasons") or []
            hook = ""
            sym_key = str(sym).strip().lower()
            sym_evidence = [n for n in evidence_nodes if n.get("symbol") == sym_key]
            if sym_evidence:
                debate = next(
                    (n for n in sym_evidence if n.get("event_type") == "DebateRoundEvent"),
                    None,
                )
                if debate:
                    summary = (debate.get("payload") or {}).get("evidence_summary") or debate.get(
                        "label", ""
                    )
                    hook = f"多智能体辩论证据：{summary[:80]}。"
                consensus = next(
                    (n for n in sym_evidence if n.get("event_type") == "ArbiterConsensusEvent"),
                    None,
                )
                if consensus and not hook:
                    hook = f"仲裁结论：{consensus.get('label', '')}。"
            if success_patterns and sym:
                for pat in success_patterns:
                    if sym in (pat.get("symbols") or []):
                        hook = (hook or "") + "这与您历史成功模式高度吻合。"
                        break
                if not hook and frequent and sym not in frequent:
                    hook = "新标的，但信号结构与您偏好板块相近。"
            narrative = f"{name}（{sym}）：{'；'.join(reasons[:2]) or '综合评分入选'}。{hook}".strip()
            rec_narratives.append({"symbol": sym, "narrative": narrative})

        closing = briefing.get("summary") or "祝您今日投研顺利。"
        if causal_hooks:
            closing = causal_hooks[0] + "。" + closing

        return {
            "opening": opening,
            "market_narrative": (
                f"当前市场判定为 {market_env.get('regime', 'unknown')}，"
                f"建议策略：{', '.join(market_env.get('recommended_strategies') or []) or '均衡配置'}。"
            ),
            "recommendation_narratives": rec_narratives,
            "personalized_closing": closing,
            "causal_hooks": causal_hooks,
        }

    @staticmethod
    def _success_patterns(knowledge: dict[str, Any]) -> list[dict[str, Any]]:
        patterns = knowledge.get("related_decision_patterns") or []
        if patterns:
            wins = [
                p
                for p in patterns
                if str(p.get("outcome") or "").lower() in _SUCCESS_OUTCOMES
            ]
            return wins or patterns
        return []

    @staticmethod
    def _merge_rec_narratives(
        briefing: dict[str, Any],
        llm_recs: Any,
        fallback: dict[str, Any],
    ) -> list[dict[str, str]]:
        by_sym: dict[str, str] = {
            str(r.get("symbol") or ""): str(r.get("narrative") or "")
            for r in (fallback.get("recommendation_narratives") or [])
        }
        if isinstance(llm_recs, list):
            for row in llm_recs:
                if isinstance(row, dict) and row.get("symbol"):
                    by_sym[str(row["symbol"])] = str(row.get("narrative") or by_sym.get(str(row["symbol"]), ""))
        recs = briefing.get("recommendations") or []
        return [
            {
                "symbol": str(r.get("symbol") or ""),
                "narrative": by_sym.get(str(r.get("symbol") or ""), ""),
            }
            for r in recs
        ]

    def _llm_causal_report(
        self,
        *,
        symbols: list[str],
        briefing: dict[str, Any],
        knowledge: dict[str, Any],
        decision_ctx: dict[str, Any],
        chain_context: list[dict[str, Any]],
        structured_narrative: dict[str, Any] | None = None,
        user_id: int | str = 0,
    ) -> dict[str, Any] | None:
        if not chain_context:
            return None
        try:
            from app.core.llm_config import get_llm_for_user

            llm = get_llm_for_user(int(user_id))
        except Exception as exc:
            logger.debug("causal report llm unavailable: %s", exc)
            return None
        prompt = self._build_causal_report_prompt(
            symbols=symbols,
            briefing=briefing,
            knowledge=knowledge,
            decision_ctx=decision_ctx,
            chain_context=chain_context,
            structured_narrative=structured_narrative,
        )
        try:
            response = llm.invoke(prompt)
            text = str(getattr(response, "content", response) or "").strip()
            parsed = self._parse_json_block(text)
            if parsed and parsed.get("report_markdown"):
                return parsed
            if text:
                return {
                    "report_markdown": text,
                    "sections": {"full": text},
                    "confidence": 0.75,
                }
        except Exception as exc:
            logger.warning("causal report LLM failed: %s", exc)
        return None

    @staticmethod
    def _template_causal_report(
        symbols: list[str],
        chain_context: list[dict[str, Any]],
        briefing: dict[str, Any],
        structured_narrative: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        lines = [f"# 因果逻辑研报 · {', '.join(symbols)}", ""]

        chains = (structured_narrative or {}).get("chains") or []
        summary = (structured_narrative or {}).get("summary") or ""

        if summary:
            lines.append(f"> {summary}")
            lines.append("")

        if chains:
            lines.append("## 因果链总览")
            lines.append("")
            for chain in chains:
                sym = chain.get("symbol", "")
                status = chain.get("status", "")
                rounds = chain.get("debate_rounds", 0)
                flow = chain.get("causal_flow", "")
                lines.append(f"### 标的: {sym} (状态: {status})")
                lines.append(f"- 辩论轮数: {rounds}")
                if flow:
                    lines.append(f"- 因果流: {flow}")
                lines.append("")

            debate_chains = [c for c in chains if c.get("debate_summary")]
            if debate_chains:
                lines.append("## 辩论证据深读")
                lines.append("")
                for chain in debate_chains:
                    sym = chain.get("symbol", "")
                    lines.append(f"### {sym}")
                    for d in chain.get("debate_summary", [])[:4]:
                        role = d.get("role", "")
                        stance = d.get("stance", "")
                        evidence = d.get("evidence", "")
                        conf = d.get("confidence", 0)
                        lines.append(f"- **{role}** ({stance}, 置信度{conf:.0%}): {evidence[:100]}")
                    lines.append("")

            consensus_chains = [c for c in chains if c.get("consensus")]
            if consensus_chains:
                lines.append("## 仲裁与风险")
                lines.append("")
                for chain in consensus_chains:
                    sym = chain.get("symbol", "")
                    cons = chain.get("consensus") or {}
                    verdict = cons.get("verdict", "")
                    conf = cons.get("confidence", 0)
                    mode = cons.get("mode", "")
                    lines.append(f"- **{sym}**: {verdict} (置信度{conf:.0%}, 模式: {mode})")
                    for corr in chain.get("corrections", []):
                        change = corr.get("change_type", "")
                        rationale = corr.get("rationale", "")
                        lines.append(f"  - 修正({change}): {rationale}")
                lines.append("")

        else:
            debate = [r for r in chain_context if r.get("event_type") == "DebateRoundEvent"]
            consensus = [r for r in chain_context if r.get("event_type") == "ArbiterConsensusEvent"]
            if debate:
                lines.append("## 多智能体辩论链")
                for row in debate[:6]:
                    summary_text = (row.get("payload") or {}).get("evidence_summary") or row.get("label", "")
                    lines.append(f"- **{row.get('label')}**: {summary_text}")
            if consensus:
                lines.append("")
                lines.append("## 仲裁结论")
                for row in consensus[:3]:
                    lines.append(f"- {row.get('label')}({row.get('symbol')})")

        market_env = briefing.get("market_environment") or {}
        if market_env:
            lines.append("")
            lines.append("## 市场环境")
            lines.append(market_env.get("regime_description", ""))
            lines.append("")

        lines.append("## 对用户的可执行建议")
        lines.append("")
        lines.append("(基于因果链证据，建议结合个人风险偏好决策)")

        md = "\n".join(lines)

        sections = {
            "causal_chain": summary if summary else "\n".join(lines[2:8]),
            "debate_summary": "",
            "arbiter_verdict": "",
            "actionable_advice": "基于因果链证据，建议结合个人风险偏好决策",
        }
        if chains:
            debate_text = []
            for c in chains:
                for d in c.get("debate_summary", [])[:2]:
                    debate_text.append(f"{d.get('role')}: {d.get('evidence', '')[:80]}")
            sections["debate_summary"] = "\n".join(debate_text)

            consensus_texts = []
            for c in chains:
                cons = c.get("consensus")
                if cons:
                    consensus_texts.append(f"{c.get('symbol')}: {cons.get('verdict', '')}")
            sections["arbiter_verdict"] = "\n".join(consensus_texts)

        return {
            "report_markdown": md,
            "sections": sections,
            "confidence": 0.65 if chains else (0.55 if chain_context else 0.35),
            "evidence_chains": chain_context,
        }

    @staticmethod
    def _build_causal_report_prompt(
        *,
        symbols: list[str],
        briefing: dict[str, Any],
        knowledge: dict[str, Any],
        decision_ctx: dict[str, Any],
        chain_context: list[dict[str, Any]],
        structured_narrative: dict[str, Any] | None = None,
    ) -> str:
        chains = (structured_narrative or {}).get("chains") or []
        chain_summary = (structured_narrative or {}).get("summary") or ""

        causal_flows = []
        for chain in chains:
            sym = chain.get("symbol", "")
            flow = chain.get("causal_flow", "")
            if flow:
                causal_flows.append(f"{sym}: {flow}")

        debate_digest = []
        for chain in chains:
            sym = chain.get("symbol", "")
            for d in chain.get("debate_summary", [])[:3]:
                role = d.get("role", "")
                stance = d.get("stance", "")
                evidence = d.get("evidence", "")[:100]
                debate_digest.append(f"{sym} | {role} ({stance}): {evidence}")

        consensus_digest = []
        for chain in chains:
            cons = chain.get("consensus")
            if cons:
                sym = chain.get("symbol", "")
                verdict = cons.get("verdict", "")
                conf = cons.get("confidence", 0)
                consensus_digest.append(f"{sym}: {verdict} (置信度{conf:.0%})")

        prompt_parts = [
            "你是资深投研主编，基于 SequenceChain 全量证据撰写**长篇因果逻辑研报**（Markdown，不少于 800 字）。",
            "",
            f"标的: {json.dumps(symbols, ensure_ascii=False)}",
            f"市场环境: {json.dumps(briefing.get('market_environment'), ensure_ascii=False)}",
            f"推荐列表: {json.dumps(briefing.get('recommendations'), ensure_ascii=False)}",
            f"用户知识: {json.dumps(knowledge.get('top_symbols'), ensure_ascii=False)}",
            f"风险上下文: {json.dumps(decision_ctx.get('risk_context'), ensure_ascii=False)}",
        ]

        if chain_summary:
            prompt_parts.append(f"因果链摘要: {chain_summary}")

        if causal_flows:
            prompt_parts.append("因果流:")
            prompt_parts.extend(f"  - {f}" for f in causal_flows)

        if debate_digest:
            prompt_parts.append("辩论要点:")
            prompt_parts.extend(f"  - {d}" for d in debate_digest[:12])

        if consensus_digest:
            prompt_parts.append("仲裁结论:")
            prompt_parts.extend(f"  - {c}" for c in consensus_digest)

        prompt_parts.extend([
            "",
            "SequenceChain 原始步骤:",
            json.dumps(chain_context, ensure_ascii=False),
            "",
            "结构要求（必须全部覆盖）：",
            "1. ## 因果链总览 — 从数据采集→辩论→仲裁→推荐的完整链条，引用因果流",
            "2. ## 辩论证据深读 — 引用具体 agent_role / stance / evidence_summary，对比多空双方",
            "3. ## 仲裁与风险 — ArbiterConsensus 结论 + CorrectionIntent 修正含义",
            "4. ## 对用户的可执行建议 — 与历史模式对照，给出具体操作建议",
            "",
            "输出纯 JSON：",
            '{"report_markdown":"...(完整 Markdown)...","sections":{"causal_chain":"...","debate_summary":"...",'
            '"arbiter_verdict":"...","actionable_advice":"..."},"confidence":0.0-1.0}',
        ])

        return "\n".join(prompt_parts)

    @staticmethod
    def _build_prompt(
        *,
        recs: list[dict[str, Any]],
        market_env: dict[str, Any],
        knowledge: dict[str, Any],
        decision_ctx: dict[str, Any],
        success_patterns: list[dict[str, Any]],
        evidence_nodes: list[dict[str, Any]],
        narrative_level: str,
    ) -> str:
        density = narrative_level
        evidence_hint = (
            "4. 必须引用 SequenceChain 证据节点，串联辩论→仲裁→推荐的因果链，禁止仅堆砌指标\n"
            if evidence_nodes
            else ""
        )
        return (
            "你是用户的私人投研官，用有温度、有因果链的中文撰写晨间简报叙事。\n"
            f"叙事密度: {density}（brief=简短, normal=适中, full=详尽）\n\n"
            f"市场环境: {json.dumps(market_env, ensure_ascii=False)}\n"
            f"候选推荐: {json.dumps(recs, ensure_ascii=False)}\n"
            f"用户关注: {json.dumps(knowledge.get('top_symbols'), ensure_ascii=False)}\n"
            f"历史成功模式: {json.dumps(success_patterns, ensure_ascii=False)}\n"
            f"决策上下文: {json.dumps(decision_ctx.get('risk_context'), ensure_ascii=False)}\n"
            f"SequenceChain 证据节点（辩论/仲裁/能力执行血缘）: "
            f"{json.dumps(evidence_nodes, ensure_ascii=False)}\n\n"
            "要求：\n"
            "1. 不要只罗列 RSI/均线术语，要解释「为什么与此用户相关」\n"
            "2. 若历史成功模式与新标的相关，明确指出模式重现\n"
            "3. 输出纯 JSON：\n"
            '{"opening":"...","market_narrative":"...","recommendation_narratives":[{"symbol":"...","narrative":"..."}],'
            '"personalized_closing":"...","causal_hooks":["..."]}\n'
            f"{evidence_hint}"
        )

    @staticmethod
    def _parse_json_block(text: str) -> dict[str, Any] | None:
        raw = (text or "").strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence:
            raw = fence.group(1).strip()
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                try:
                    data = json.loads(raw[start : end + 1])
                    return data if isinstance(data, dict) else None
                except json.JSONDecodeError:
                    return None
        return None
