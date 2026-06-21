# Remove redundant docs that have been consolidated into unified files
# Run from: E:\project\workspace\myrepo\quant-atlas\docs\

$ErrorActionPreference = "SilentlyContinue"

$files = @(
    # Product docs (consolidated into PRODUCT_MANUAL.md)
    "QUANT_ATLAS_PRODUCT_DOCUMENTATION.md",
    "QUANT_ATLAS_PRODUCT_DOCUMENTATION_PART2.md",
    "QUANT_ATLAS_PRODUCT_DOCUMENTATION_PART3.md",
    "QUANT_ATLAS_PRODUCT_DOCUMENTATION_APPENDIX.md",
    "QUANT_ATLAS_平台手册.md",

    # Architecture docs (consolidated into ARCHITECTURE.md)
    "refactoring_plan.md",
    "refactoring_plan_phase5.md",
    "refactoring_plan_phase6.md",
    "refactoring_plan_phase9.md",
    "refactoring_plan_phase13.md",
    "ARCHITECTURE_REDESIGN.md",
    "ARCHITECTURE_ANALYSIS.md",
    "APPLICATION_ANALYSIS.md",
    "full-platform-refactor-roadmap_5a99d237.plan.md",
    "REMAINING_ISSUES.md",
    "ARCHITECTURE_TODO.md",
    "REFACTORING_LOG1.md",

    # Deployment docs (consolidated into DEPLOYMENT.md)
    "DEPLOYMENT_MATRIX.md",
    "QLIB_DEPLOY.md",
    "RUN_STACK_DEPLOY.md",

    # Agent/Strategy optimization docs (consolidated into OPTIMIZATION_RECORDS.md)
    "midify_plan.md",
    "midify_plan2.md",
    "midify_plan3.md",
    "midify_plan4.md",
    "midify_plan5.md",
    "midify_plan6.md",
    "midify_plan7.md",
    "midify_plan8.md",
    "midify_plan9.md",
    "midify_plan10.md",
    "midify_plan11.md",
    "midify_plan12.md",
    "midify_plan13.md",
    "strategy_plan.md",
    "strategy_plan1.md",
    "strategy_plan2.md",
    "strategy_plan3.md",
    "strategy_plan4.md",
    "STRATEGY_OPTIMIZATION_RECORD.md",
    "STRATEGY_PLAN1_OPTIMIZATION_RECORD.md",
    "AGENT_OPTIMIZATION_RECORD.md",
    "rdagent_plan.md",
    "trading_agents.md",
    "qlib_rdagent_loop.md",
    "qlib_rd_trifecta_playbook.md",
    "RD_AGENT_QLIB_FLASK_FLOW.md",
    "QLIB_RD_AGENT_ENHANCEMENT.md",
    "agents_self_contained.md",
    "OPTIMIZATION_SUMMARY.md",
    "OPTIMIZATION_ADVICE.md",

    # Testing docs (consolidated into TESTING.md)
    "API_TEST_PLAN.md",
    "API_TEST_STATUS.md",
    "API_TEST_FINAL.md",
    "API_TEST_COMPREHENSIVE.md",
    "test_plan.md",
    "testing_strategy.md",

    # Legacy/Scripts docs (consolidated into LEGACY_SCRIPTS.md)
    "SCRIPTS_MIGRATION_PLAN.md",
    "scripts_inventory.md",
    "LEGACY_STATUS.md",
    "PLATFORM_BOUNDARY.md",

    # Roadmap docs (consolidated into ROADMAP.md)
    "ROADMAP_EXECUTION_BACKLOG_2026Q2.md",
    "NEXT_ENHANCEMENTS.md",
    "NEXT_PHASE.md",
    "PHASE18_PLAN.md",
    "PHASE19_PLAN.md",
    "PHASE20_PLAN.md",
    "roadmap_qlib_rd_agent.md",
    "ROADMAP_FROM_CASE.md",

    # Misc plans (consolidated into MISC_PLANS_AND_ANALYSIS.md)
    "plan.md",
    "plan1.md",
    "plan2.md",
    "plan_op.md",
    "plan_op1.md",
    "ai_plan.md",
    "user_plan.md",
    "final_plan.md",
    "final_plan重构_ceccd1a1.plan.md",
    "用户价值路线_f3758b30.plan.md",
    "用户价值路线图plan.md",
    "ui_plan.md",
    "i18n_plan.md",
    "dataware_plan.md",
    "case.md",
    "self_stock.md",
    "CHAT_SESSION_LOG.md",
    "plan_case1.md",
    "quantatlas_plan1.md",
    "quantatlas_plan2.md",
    "quant_plan.md",
    "six_anasis_report.md",
    "六分析报告_data_gap.md"
)

$count = 0
foreach ($f in $files) {
    if (Test-Path $f) {
        Remove-Item $f -Force
        Write-Host "  Deleted: $f"
        $count++
    }
}

Write-Host "`n=== Done ==="
Write-Host "Deleted $count files."
Write-Host "Remaining:"
Write-Host "  PRODUCT_MANUAL.md"
Write-Host "  ARCHITECTURE.md"
Write-Host "  DEPLOYMENT.md"
Write-Host "  OPTIMIZATION_RECORDS.md"
Write-Host "  TESTING.md"
Write-Host "  LEGACY_SCRIPTS.md"
Write-Host "  ROADMAP.md"
Write-Host "  MISC_PLANS_AND_ANALYSIS.md"
Write-Host "  CHANGELOG.md"
Write-Host "  USAGE_GUIDE.md"
Write-Host "  batch_delete_redundant.ps1 (this file)"
Write-Host ""
Write-Host "Still need manual removal:"
Write-Host "  可行性分析.docx"
Write-Host "  华银电力.xlsx"
Write-Host "  专业财务文件字段含义对照表.txt"
