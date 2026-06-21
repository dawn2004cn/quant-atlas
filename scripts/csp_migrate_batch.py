"""One-off batch CSP inline-handler migration for templates."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "presentation" / "web" / "templates"
INLINE = re.compile(r"(?<![\w.])\bon(click|change|keydown|keyup|submit|input|load)\s*=", re.I)


def count(path: Path) -> int:
    return len(INLINE.findall(path.read_text(encoding="utf-8", errors="replace")))


def migrate_ai_hedge_fund() -> None:
    p = ROOT / "ai_hedge_fund.html"
    t = p.read_text(encoding="utf-8")
    t = t.replace(' onclick="toggleGroup(this.parentElement)"', ' data-ahf-action="toggle-group"')
    t = re.sub(r" onclick=\"toggleAgent\(this, '([^']+)'\)\"", ' data-ahf-action="toggle-agent"', t)
    t = re.sub(
        r'onclick="selectGroup\(\'([^\']+)\', (true|false)\); event\.stopPropagation\(\);"',
        lambda m: (
            f'data-ahf-action="select-group" data-group="{m.group(1)}" '
            f'data-select="{m.group(2)}" type="button"'
        ),
        t,
    )
    t = t.replace('onclick="selectAllAgents()"', 'data-ahf-action="select-all-agents" type="button"')
    t = t.replace('onclick="deselectAllAgents()"', 'data-ahf-action="deselect-all-agents" type="button"')
    t = t.replace('onclick="runAnalysis()"', 'data-ahf-action="run-analysis" type="button"')
    handler = """
function handleAhfAction(event) {
    const el = event.target.closest('[data-ahf-action]');
    if (!el) return;
    const action = el.dataset.ahfAction;
    if (action === 'toggle-group') {
        const group = el.parentElement;
        if (group) toggleGroup(group);
        return;
    }
    if (action === 'select-group') {
        event.stopPropagation();
        selectGroup(el.dataset.group || '', el.dataset.select === 'true');
        return;
    }
    if (action === 'toggle-agent') {
        const card = el.classList.contains('ai-agent-card') ? el : el.closest('.ai-agent-card');
        if (card) toggleAgent(card, el.dataset.agent || '');
        return;
    }
    if (action === 'select-all-agents') selectAllAgents();
    else if (action === 'deselect-all-agents') deselectAllAgents();
    else if (action === 'run-analysis') runAnalysis();
}
"""
    old = "document.addEventListener('DOMContentLoaded', function() {\n    updateAllGroupCounts();\n});"
    new = (
        handler
        + "\ndocument.addEventListener('DOMContentLoaded', function() {\n"
        + "    document.addEventListener('click', handleAhfAction);\n"
        + "    updateAllGroupCounts();\n});"
    )
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print("ai_hedge_fund", count(p))


def migrate_expert_teams() -> None:
    p = ROOT / "expert_teams.html"
    t = p.read_text(encoding="utf-8")
    t = re.sub(
        r"onclick=\"openRunModal\('((?:[^'\\]|\\.)*)', '((?:[^'\\]|\\.)*)', '((?:[^'\\]|\\.)*)'\)\"",
        lambda m: (
            f'data-et-action="open-run" data-team-id="{m.group(1)}" '
            f'data-team-name="{m.group(2)}" data-team-desc="{m.group(3)}" '
            f'role="button" tabindex="0"'
        ),
        t,
    )
    t = t.replace('onclick="closeRunModal()"', 'data-et-action="close-modal" type="button"')
    t = t.replace('onclick="runTeam()"', 'data-et-action="run-team" type="button"')
    handler = """
function handleEtAction(event) {
    const el = event.target.closest('[data-et-action]');
    if (!el) return;
    const action = el.dataset.etAction;
    if (action === 'open-run') {
        openRunModal(el.dataset.teamId || '', el.dataset.teamName || '', el.dataset.teamDesc || '');
    } else if (action === 'close-modal') closeRunModal();
    else if (action === 'run-team') runTeam();
}
document.addEventListener('click', handleEtAction);
"""
    if "handleEtAction" not in t:
        t = t.replace("</script>", handler + "\n</script>", 1)
    p.write_text(t, encoding="utf-8")
    print("expert_teams", count(p))


def migrate_alpha_factory() -> None:
    p = ROOT / "alpha_factory.html"
    t = p.read_text(encoding="utf-8")
    t = re.sub(r" onclick=\"switchTab\('([^']+)'\)\"", r' data-af-action="switch-tab" data-tab="\1"', t)
    t = re.sub(
        r"onclick=\"setFormula\('((?:[^'\\]|\\.)*)'\)\"",
        lambda m: f'data-af-action="set-formula" data-formula="{m.group(1)}" type="button"',
        t,
    )
    replacements = {
        'onclick="submitExperiment(event)"': 'data-af-action="submit-experiment" type="button"',
        'onclick="loadFactors()"': 'data-af-action="load-factors" type="button"',
        'onclick="validateFormula()"': 'data-af-action="validate-formula" type="button"',
        'onclick="loadCorrelation()"': 'data-af-action="load-correlation" type="button"',
        'onclick="loadOnlineStatus()"': 'data-af-action="load-online-status" type="button"',
        'onclick="loadModelZoo()"': 'data-af-action="load-model-zoo" type="button"',
        'onclick="submitPaperTrading()"': 'data-af-action="submit-paper" type="button"',
        'onclick="loadPaperStatus()"': 'data-af-action="load-paper-status" type="button"',
        'onclick="getModelRecommendation()"': 'data-af-action="model-recommendation" type="button"',
        'onclick="enableWeeklyMeeting()"': 'data-af-action="enable-weekly" type="button"',
        'onclick="disableWeeklyMeeting()"': 'data-af-action="disable-weekly" type="button"',
        'onclick="runWeeklyScan()"': 'data-af-action="weekly-scan" type="button"',
        'onclick="loadPipelineStatus()"': 'data-af-action="load-pipeline" type="button"',
    }
    for old, new in replacements.items():
        t = t.replace(old, new)
    handler = """
function handleAfAction(event) {
    const el = event.target.closest('[data-af-action]');
    if (!el) return;
    const action = el.dataset.afAction;
    if (action === 'switch-tab') switchTab(el.dataset.tab || 'experiment');
    else if (action === 'set-formula') setFormula(el.dataset.formula || '');
    else if (action === 'submit-experiment') submitExperiment(event);
    else if (action === 'load-factors') loadFactors();
    else if (action === 'validate-formula') validateFormula();
    else if (action === 'load-correlation') loadCorrelation();
    else if (action === 'load-online-status') loadOnlineStatus();
    else if (action === 'load-model-zoo') loadModelZoo();
    else if (action === 'submit-paper') submitPaperTrading();
    else if (action === 'load-paper-status') loadPaperStatus();
    else if (action === 'model-recommendation') getModelRecommendation();
    else if (action === 'enable-weekly') enableWeeklyMeeting();
    else if (action === 'disable-weekly') disableWeeklyMeeting();
    else if (action === 'weekly-scan') runWeeklyScan();
    else if (action === 'load-pipeline') loadPipelineStatus();
}
document.addEventListener('click', handleAfAction);
"""
    if "handleAfAction" not in t:
        t = t.replace("</script>", handler + "\n</script>", 1)
    p.write_text(t, encoding="utf-8")
    print("alpha_factory", count(p))


def migrate_retail_assistant() -> None:
    p = ROOT / "retail_assistant.html"
    t = p.read_text(encoding="utf-8")
    replacements = {
        """onclick="showToast('Pro 订阅开发中，请添加微信: quant_atlas 详谈', 'info')" """: (
            'data-ra-action="toast" data-toast-msg="Pro 订阅开发中，请添加微信: quant_atlas 详谈" '
            'data-toast-type="info" type="button"'
        ),
        """onclick="showToast('VIP 订阅开发中，请添加微信: quant_atlas 详谈', 'info')" """: (
            'data-ra-action="toast" data-toast-msg="VIP 订阅开发中，请添加微信: quant_atlas 详谈" '
            'data-toast-type="info" type="button"'
        ),
        'onclick="loadRefactorStatus()"': 'data-ra-action="load-refactor" type="button"',
        'onclick="loadPsychology(false)"': 'data-ra-action="load-psychology" data-push="false" type="button"',
        'onclick="runPsychologyScan(false)"': 'data-ra-action="psychology-scan" type="button"',
        'onclick="loadPsychology(true)"': 'data-ra-action="load-psychology" data-push="true" type="button"',
        'onclick="loadShadowMirror()"': 'data-ra-action="load-shadow" type="button"',
        'onclick="loadOverview()"': 'data-ra-action="load-overview" type="button"',
        'onclick="loadKnowledge()"': 'data-ra-action="load-knowledge" type="button"',
        'onclick="addKnowledgeSymbolToWatchlist()"': 'data-ra-action="add-watchlist" type="button"',
        """onclick="showToast('请添加微信: quant_atlas 详谈', 'info')" """: (
            'data-ra-action="toast" data-toast-msg="请添加微信: quant_atlas 详谈" data-toast-type="info" type="button"'
        ),
        'onclick="raHideError();loadOverview();"': 'data-ra-action="retry-overview" type="button"',
        'onclick="raHideError();loadAccessPolicy();"': 'data-ra-action="retry-access" type="button"',
    }
    for old, new in replacements.items():
        t = t.replace(old, new)
    handler = """
function handleRaAction(event) {
    const el = event.target.closest('[data-ra-action]');
    if (!el) return;
    const action = el.dataset.raAction;
    if (action === 'toast') showToast(el.dataset.toastMsg || '', el.dataset.toastType || 'info');
    else if (action === 'load-refactor') loadRefactorStatus();
    else if (action === 'load-psychology') loadPsychology(el.dataset.push === 'true');
    else if (action === 'psychology-scan') runPsychologyScan(false);
    else if (action === 'load-shadow') loadShadowMirror();
    else if (action === 'load-overview') loadOverview();
    else if (action === 'load-knowledge') loadKnowledge();
    else if (action === 'add-watchlist') addKnowledgeSymbolToWatchlist();
    else if (action === 'retry-overview') { raHideError(); loadOverview(); }
    else if (action === 'retry-access') { raHideError(); loadAccessPolicy(); }
}
"""
    t = t.replace(
        "$(function() {",
        handler + "\n$(function() {\n    document.addEventListener('click', handleRaAction);",
        1,
    )
    p.write_text(t, encoding="utf-8")
    print("retail_assistant", count(p))


def migrate_quant_lab() -> None:
    p = ROOT / "quant_lab.html"
    t = p.read_text(encoding="utf-8")
    t = t.replace('onclick="runSimulation()"', 'data-ql-action="run-simulation" type="button"')
    t = t.replace('onclick="sendToEvolution()"', 'data-ql-action="send-evolution" type="button"')
    t = re.sub(
        r'onclick="insertOp\(\'((?:[^\'\\]|\\.)*)\'\)"',
        lambda m: f'data-ql-action="insert-op" data-op="{m.group(1)}" role="button" tabindex="0"',
        t,
    )
    handler = """
function handleQlAction(event) {
    const el = event.target.closest('[data-ql-action]');
    if (!el) return;
    const action = el.dataset.qlAction;
    if (action === 'run-simulation') runSimulation();
    else if (action === 'send-evolution') sendToEvolution();
    else if (action === 'insert-op') insertOp(el.dataset.op || '');
}
document.addEventListener('click', handleQlAction);
"""
    if "handleQlAction" not in t:
        t = t.replace("</script>", handler + "\n</script>", 1)
    p.write_text(t, encoding="utf-8")
    print("quant_lab", count(p))


def migrate_agent_center() -> None:
    p = ROOT / "agent_center.html"
    t = p.read_text(encoding="utf-8")
    t = re.sub(
        r'onclick="switchTab\(\'([^\']+)\'\)"',
        lambda m: f'data-ac-action="switch-tab" data-tab="{m.group(1)}" type="button"',
        t,
    )
    t = t.replace('onclick="closeAgentDetail()"', 'data-ac-action="close-detail" type="button"')
    t = re.sub(
        r'onclick="showAgentDetail\(\'([^\']+)\'\)"',
        lambda m: f'data-ac-action="show-agent" data-agent-id="{m.group(1)}" role="button" tabindex="0"',
        t,
    )
    handler = """
function handleAcAction(event) {
    const el = event.target.closest('[data-ac-action]');
    if (!el) return;
    const action = el.dataset.acAction;
    if (action === 'switch-tab') switchTab(el.dataset.tab || 'all');
    else if (action === 'close-detail') closeAgentDetail();
    else if (action === 'show-agent') showAgentDetail(el.dataset.agentId || '');
}
document.addEventListener('click', handleAcAction);
"""
    if "handleAcAction" not in t:
        t = t.replace("</script>", handler + "\n</script>", 1)
    p.write_text(t, encoding="utf-8")
    print("agent_center", count(p))


def migrate_backtest() -> None:
    p = ROOT / "backtest.html"
    t = p.read_text(encoding="utf-8")
    replacements = {
        'onclick="copyConfig()"': 'data-bt-action="copy-config" type="button"',
        'onclick="startStrategyDuel()"': 'data-bt-action="strategy-duel" type="button"',
        'onclick="simulateBuyTheDip()"': 'data-bt-action="buy-the-dip" type="button"',
        'onclick="findBloodiedPearls()"': 'data-bt-action="bloodied-pearls" type="button"',
    }
    for old, new in replacements.items():
        t = t.replace(old, new)
    t = t.replace('onchange="toggleCounterMode()"', 'id="counterModeToggle"')
    # fix duplicate id if needed - read line
    if 'id="counterModeToggle" id="counterModeToggle"' in t:
        t = t.replace('id="counterModeToggle" id="counterModeToggle"', 'id="counterModeToggle"')
    handler = """
function handleBtAction(event) {
    const el = event.target.closest('[data-bt-action]');
    if (!el) return;
    const action = el.dataset.btAction;
    if (action === 'copy-config') copyConfig();
    else if (action === 'strategy-duel') startStrategyDuel();
    else if (action === 'buy-the-dip') simulateBuyTheDip();
    else if (action === 'bloodied-pearls') findBloodiedPearls();
}
document.addEventListener('click', handleBtAction);
document.getElementById('counterModeToggle')?.addEventListener('change', toggleCounterMode);
"""
    if "handleBtAction" not in t:
        t = t.replace("</script>", handler + "\n</script>", 1)
    p.write_text(t, encoding="utf-8")
    print("backtest", count(p))


def migrate_stock_selector() -> None:
    p = ROOT / "stock_selector.html"
    t = p.read_text(encoding="utf-8")
    t = t.replace('onclick="openLegoEditor()"', 'data-ss-action="open-lego" type="button"')
    t = re.sub(
        r"onclick=\"applyLegoPreset\('([^']+)'\)\"",
        lambda m: f'data-ss-action="lego-preset" data-preset="{m.group(1)}" role="button" tabindex="0"',
        t,
    )
    handler = """
function handleSsAction(event) {
    const el = event.target.closest('[data-ss-action]');
    if (!el) return;
    const action = el.dataset.ssAction;
    if (action === 'open-lego') openLegoEditor();
    else if (action === 'lego-preset') applyLegoPreset(el.dataset.preset || '');
}
document.addEventListener('click', handleSsAction);
"""
    if "handleSsAction" not in t:
        t = t.replace("</script>", handler + "\n</script>", 1)
    p.write_text(t, encoding="utf-8")
    print("stock_selector", count(p))


def fix_onchange_handlers() -> None:
    # expert_teams
    p = ROOT / "expert_teams.html"
    t = p.read_text(encoding="utf-8")
    t = t.replace(' onchange="filterTeams()"', '')
    if "filterTeams" in t and "$('#categoryFilter').on('change'" not in t:
        t = t.replace(
            "document.addEventListener('click', handleEtAction);",
            "document.addEventListener('click', handleEtAction);\n"
            "document.getElementById('categoryFilter')?.addEventListener('change', filterTeams);",
        )
    p.write_text(t, encoding="utf-8")
    print("expert_teams", count(p))

    # alpha_factory
    p = ROOT / "alpha_factory.html"
    t = p.read_text(encoding="utf-8")
    t = t.replace(' onchange="updateGoalDescription()"', '')
    t = t.replace(' onchange="loadFactors()"', '')
    if "$('#experimentGoal').on('change'" not in t:
        t = t.replace(
            "document.addEventListener('click', handleAfAction);",
            "document.addEventListener('click', handleAfAction);\n"
            "document.getElementById('experimentGoal')?.addEventListener('change', updateGoalDescription);\n"
            "document.getElementById('filterRegime')?.addEventListener('change', loadFactors);",
        )
    p.write_text(t, encoding="utf-8")
    print("alpha_factory", count(p))


if __name__ == "__main__":
    migrate_ai_hedge_fund()
    migrate_expert_teams()
    migrate_alpha_factory()
    migrate_retail_assistant()
    migrate_quant_lab()
    migrate_agent_center()
    migrate_backtest()
    migrate_stock_selector()
    fix_onchange_handlers()
