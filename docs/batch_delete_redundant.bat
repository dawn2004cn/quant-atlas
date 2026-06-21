@echo off
REM Delete redundant docs that have been consolidated into unified files
setlocal

cd /d "%~dp0"

echo === Removing redundant docs ===

REM Product docs (consolidated into PRODUCT_MANUAL.md)
del /Q "QUANT_ATLAS_PRODUCT_DOCUMENTATION.md" 2>nul
del /Q "QUANT_ATLAS_PRODUCT_DOCUMENTATION_PART2.md" 2>nul
del /Q "QUANT_ATLAS_PRODUCT_DOCUMENTATION_PART3.md" 2>nul
del /Q "QUANT_ATLAS_PRODUCT_DOCUMENTATION_APPENDIX.md" 2>nul
del /Q "QUANT_ATLAS_平台手册.md" 2>nul

REM Architecture docs (consolidated into ARCHITECTURE.md)
del /Q "refactoring_plan.md" 2>nul
del /Q "refactoring_plan_phase5.md" 2>nul
del /Q "refactoring_plan_phase6.md" 2>nul
del /Q "refactoring_plan_phase9.md" 2>nul
del /Q "refactoring_plan_phase13.md" 2>nul
del /Q "ARCHITECTURE_REDESIGN.md" 2>nul
del /Q "ARCHITECTURE_ANALYSIS.md" 2>nul
del /Q "APPLICATION_ANALYSIS.md" 2>nul
del /Q "full-platform-refactor-roadmap_5a99d237.plan.md" 2>nul
del /Q "REMAINING_ISSUES.md" 2>nul
del /Q "ARCHITECTURE_TODO.md" 2>nul
del /Q "REFACTORING_LOG1.md" 2>nul

REM Deployment docs (consolidated into DEPLOYMENT.md)
del /Q "DEPLOYMENT_MATRIX.md" 2>nul
del /Q "QLIB_DEPLOY.md" 2>nul
del /Q "RUN_STACK_DEPLOY.md" 2>nul

REM Agent/Strategy optimization docs (consolidated into OPTIMIZATION_RECORDS.md)
del /Q "midify_plan.md" 2>nul
del /Q "midify_plan2.md" 2>nul
del /Q "midify_plan3.md" 2>nul
del /Q "midify_plan4.md" 2>nul
del /Q "midify_plan5.md" 2>nul
del /Q "midify_plan6.md" 2>nul
del /Q "midify_plan7.md" 2>nul
del /Q "midify_plan8.md" 2>nul
del /Q "midify_plan9.md" 2>nul
del /Q "midify_plan10.md" 2>nul
del /Q "midify_plan11.md" 2>nul
del /Q "midify_plan12.md" 2>nul
del /Q "midify_plan13.md" 2>nul
del /Q "strategy_plan.md" 2>nul
del /Q "strategy_plan1.md" 2>nul
del /Q "strategy_plan2.md" 2>nul
del /Q "strategy_plan3.md" 2>nul
del /Q "strategy_plan4.md" 2>nul
del /Q "STRATEGY_OPTIMIZATION_RECORD.md" 2>nul
del /Q "STRATEGY_PLAN1_OPTIMIZATION_RECORD.md" 2>nul
del /Q "AGENT_OPTIMIZATION_RECORD.md" 2>nul
del /Q "rdagent_plan.md" 2>nul
del /Q "trading_agents.md" 2>nul
del /Q "qlib_rdagent_loop.md" 2>nul
del /Q "qlib_rd_trifecta_playbook.md" 2>nul
del /Q "RD_AGENT_QLIB_FLASK_FLOW.md" 2>nul
del /Q "QLIB_RD_AGENT_ENHANCEMENT.md" 2>nul
del /Q "agents_self_contained.md" 2>nul
del /Q "OPTIMIZATION_SUMMARY.md" 2>nul
del /Q "OPTIMIZATION_ADVICE.md" 2>nul

REM Testing docs (consolidated into TESTING.md)
del /Q "API_TEST_PLAN.md" 2>nul
del /Q "API_TEST_STATUS.md" 2>nul
del /Q "API_TEST_FINAL.md" 2>nul
del /Q "API_TEST_COMPREHENSIVE.md" 2>nul
del /Q "test_plan.md" 2>nul
del /Q "testing_strategy.md" 2>nul

REM Legacy/Scripts docs (consolidated into LEGACY_SCRIPTS.md)
del /Q "SCRIPTS_MIGRATION_PLAN.md" 2>nul
del /Q "scripts_inventory.md" 2>nul
del /Q "LEGACY_STATUS.md" 2>nul
del /Q "PLATFORM_BOUNDARY.md" 2>nul

REM Roadmap docs (consolidated into ROADMAP.md)
del /Q "ROADMAP_EXECUTION_BACKLOG_2026Q2.md" 2>nul
del /Q "NEXT_ENHANCEMENTS.md" 2>nul
del /Q "NEXT_PHASE.md" 2>nul
del /Q "PHASE18_PLAN.md" 2>nul
del /Q "PHASE19_PLAN.md" 2>nul
del /Q "PHASE20_PLAN.md" 2>nul
del /Q "roadmap_qlib_rd_agent.md" 2>nul
del /Q "ROADMAP_FROM_CASE.md" 2>nul

REM Misc plans (consolidated into MISC_PLANS_AND_ANALYSIS.md)
del /Q "plan.md" 2>nul
del /Q "plan1.md" 2>nul
del /Q "plan2.md" 2>nul
del /Q "plan_op.md" 2>nul
del /Q "plan_op1.md" 2>nul
del /Q "ai_plan.md" 2>nul
del /Q "user_plan.md" 2>nul
del /Q "final_plan.md" 2>nul
del /Q "final_plan重构_ceccd1a1.plan.md" 2>nul
del /Q "用户价值路线_f3758b30.plan.md" 2>nul
del /Q "用户价值路线图plan.md" 2>nul
del /Q "ui_plan.md" 2>nul
del /Q "i18n_plan.md" 2>nul
del /Q "dataware_plan.md" 2>nul
del /Q "case.md" 2>nul
del /Q "self_stock.md" 2>nul
del /Q "CHAT_SESSION_LOG.md" 2>nul
del /Q "plan_case1.md" 2>nul
del /Q "quantatlas_plan1.md" 2>nul
del /Q "quantatlas_plan2.md" 2>nul
del /Q "quant_plan.md" 2>nul
del /Q "六分析报告.md" 2>nul 2>nul
del /Q "六分析报告_data_gap.md" 2>nul 2>nul
del /Q "六分析报告.md" 2>nul 2>nul

echo === Done ===
echo Remaining files should be:
echo   PRODUCT_MANUAL.md, ARCHITECTURE.md, DEPLOYMENT.md
echo   OPTIMIZATION_RECORDS.md, TESTING.md, LEGACY_SCRIPTS.md
echo   ROADMAP.md, MISC_PLANS_AND_ANALYSIS.md
echo   CHANGELOG.md, USAGE_GUIDE.md
echo   Plus .docx/.xlsx/.txt files (moved to archive/)
echo   Plus refactor/ subdirectory
