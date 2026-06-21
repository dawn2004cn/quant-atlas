import { BrowserRouter, Route, Routes } from "react-router-dom";
import { lazy, Suspense } from "react";
import { FeatureGate } from "./components/FeatureGate";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DashboardPage } from "./pages/Dashboard";
import { LoginPage } from "./pages/Login";
import { NotFoundPage } from "./pages/NotFound";
import { StockDetailPage } from "./pages/StockDetail";

const AlphaFactoryPage = lazy(() => import("./pages/AlphaFactory").then((m) => ({ default: m.AlphaFactoryPage })));
const BacktestPage = lazy(() => import("./pages/Backtest").then((m) => ({ default: m.BacktestPage })));
const ExperimentReportPage = lazy(() => import("./pages/ExperimentReport").then((m) => ({ default: m.ExperimentReportPage })));
const MarketplacePage = lazy(() => import("./pages/Marketplace").then((m) => ({ default: m.MarketplacePage })));
const MarketPanoramaPage = lazy(() => import("./pages/MarketPanorama").then((m) => ({ default: m.MarketPanoramaPage })));
const RunHistoryPage = lazy(() => import("./pages/RunHistory").then((m) => ({ default: m.RunHistoryPage })));
const SignalFlagPage = lazy(() => import("./pages/SignalFlag").then((m) => ({ default: m.SignalFlagPage })));

/* M1 — Core Flow Pages */
const PortfolioPage = lazy(() => import("./pages/Portfolio").then((m) => ({ default: m.PortfolioPage })));
const PortfolioDetailPage = lazy(() => import("./pages/PortfolioDetail").then((m) => ({ default: m.PortfolioDetailPage })));
const HotSectorsPage = lazy(() => import("./pages/HotSectors").then((m) => ({ default: m.HotSectorsPage })));
const GlobalRadarPage = lazy(() => import("./pages/GlobalRadar").then((m) => ({ default: m.GlobalRadarPage })));
const SelfStocksPage = lazy(() => import("./pages/SelfStocks").then((m) => ({ default: m.SelfStocksPage })));
const StockSelectorPage = lazy(() => import("./pages/StockSelector").then((m) => ({ default: m.StockSelectorPage })));
const LongTermSelectPage = lazy(() => import("./pages/LongTermSelect").then((m) => ({ default: m.LongTermSelectPage })));
const StrategyComparePage = lazy(() => import("./pages/StrategyCompare").then((m) => ({ default: m.StrategyComparePage })));
const StrategySnapshotsPage = lazy(() => import("./pages/StrategySnapshots").then((m) => ({ default: m.StrategySnapshotsPage })));
const DecisionSnapshotPage = lazy(() => import("./pages/DecisionSnapshot").then((m) => ({ default: m.DecisionSnapshotPage })));
const DecisionSnapshotPublicPage = lazy(() => import("./pages/DecisionSnapshot").then((m) => ({ default: m.DecisionSnapshotPublicPage })));
const NLStrategyPage = lazy(() => import("./pages/NLStrategy").then((m) => ({ default: m.NLStrategyPage })));
const StrategyWizardPage = lazy(() => import("./pages/StrategyWizard").then((m) => ({ default: m.StrategyWizardPage })));
const TdxBlocksPage = lazy(() => import("./pages/TdxBlocks").then((m) => ({ default: m.TdxBlocksPage })));

/* M2 — Collaborative & Swarm Pages */
const CollaborationWorkspacePage = lazy(() => import("./pages/CollaborationWorkspace").then((m) => ({ default: m.CollaborationWorkspacePage })));
const MessageCenterPage = lazy(() => import("./pages/MessageCenter").then((m) => ({ default: m.MessageCenterPage })));
const TaskCenterPage = lazy(() => import("./pages/TaskCenter").then((m) => ({ default: m.TaskCenterPage })));
const TaskDetailPage = lazy(() => import("./pages/TaskDetail").then((m) => ({ default: m.TaskDetailPage })));
const SwarmDashboardPage = lazy(() => import("./pages/SwarmDashboard").then((m) => ({ default: m.SwarmDashboardPage })));
const SwarmDesignerPage = lazy(() => import("./pages/SwarmDesigner").then((m) => ({ default: m.SwarmDesignerPage })));
const SignalObservationsPage = lazy(() => import("./pages/SignalObservations").then((m) => ({ default: m.SignalObservationsPage })));
const VoiceBriefingPage = lazy(() => import("./pages/VoiceBriefing").then((m) => ({ default: m.VoiceBriefingPage })));
const ResearchCanvasPage = lazy(() => import("./pages/ResearchCanvas").then((m) => ({ default: m.ResearchCanvasPage })));
const ResearchPipelinePage = lazy(() => import("./pages/ResearchPipeline").then((m) => ({ default: m.ResearchPipelinePage })));

/* M2 — AI & Analytics Pages */
const AIChatPage = lazy(() => import("./pages/AIChat").then((m) => ({ default: m.AIChatPage })));
const AIAnalysisPage = lazy(() => import("./pages/AIAnalysis").then((m) => ({ default: m.AIAnalysisPage })));
const AIResearchReportPage = lazy(() => import("./pages/AIResearchReport").then((m) => ({ default: m.AIResearchReportPage })));
const AIHedgeFundPage = lazy(() => import("./pages/AIHedgeFund").then((m) => ({ default: m.AIHedgeFundPage })));
const AICommitteeDashboardPage = lazy(() => import("./pages/AICommitteeDashboard").then((m) => ({ default: m.AICommitteeDashboardPage })));
const AICommitteeSelectionPage = lazy(() => import("./pages/AICommitteeSelection").then((m) => ({ default: m.AICommitteeSelectionPage })));
const AIInvestmentCommitteePage = lazy(() => import("./pages/AIInvestmentCommittee").then((m) => ({ default: m.AIInvestmentCommitteePage })));
const WarRoomPage = lazy(() => import("./pages/WarRoom").then((m) => ({ default: m.WarRoomPage })));

/* M2 — Secondary Data Pages */
const AlertCenterPage = lazy(() => import("./pages/AlertCenter").then((m) => ({ default: m.AlertCenterPage })));
const YanbaoHubPage = lazy(() => import("./pages/YanbaoHub").then((m) => ({ default: m.YanbaoHubPage })));
const LonghuBangPage = lazy(() => import("./pages/LonghuBang").then((m) => ({ default: m.LonghuBangPage })));
const SelectionResultPage = lazy(() => import("./pages/SelectionResult").then((m) => ({ default: m.SelectionResultPage })));
const InvestmentManagersPage = lazy(() => import("./pages/InvestmentManagers").then((m) => ({ default: m.InvestmentManagersPage })));
const InvestmentManagerDetailPage = lazy(() => import("./pages/InvestmentManagerDetail").then((m) => ({ default: m.InvestmentManagerDetailPage })));
const ExpertTeamsPage = lazy(() => import("./pages/ExpertTeams").then((m) => ({ default: m.ExpertTeamsPage })));
const AgentCenterPage = lazy(() => import("./pages/AgentCenter").then((m) => ({ default: m.AgentCenterPage })));
const DecisionReplaySpacePage = lazy(() => import("./pages/DecisionReplaySpace").then((m) => ({ default: m.DecisionReplaySpacePage })));

/* Factor Pages */
const FactorRepositoryPage = lazy(() => import("./pages/FactorRepository"));
const FactorEvolutionPage = lazy(() => import("./pages/FactorEvolution"));
const FactorDetailPage = lazy(() => import("./pages/FactorDetail"));

/* Wraps a lazy-loaded page with Suspense + per-route ErrorBoundary */
function LazyRoute({ children, label }: { children: React.ReactNode; label?: string }) {
  return (
    <ErrorBoundary label={label}>
      <Suspense fallback={<div className="glass-card p-6 text-sm text-slate-400">加载中...</div>}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <BrowserRouter basename="/app">
      <ErrorBoundary label="Root">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="backtest" element={<LazyRoute label="Backtest"><BacktestPage /></LazyRoute>} />
              <Route path="market-panorama" element={<LazyRoute label="MarketPanorama"><MarketPanoramaPage /></LazyRoute>} />
              <Route path="runs" element={<LazyRoute label="RunHistory"><RunHistoryPage /></LazyRoute>} />
              <Route path="experiments" element={<LazyRoute label="ExperimentReport"><ExperimentReportPage /></LazyRoute>} />
              <Route
                path="marketplace"
                element={
                  <FeatureGate feature="feature_alpha_marketplace">
                    <LazyRoute label="Marketplace"><MarketplacePage /></LazyRoute>
                  </FeatureGate>
                }
              />
              <Route path="stock/:symbol" element={<ErrorBoundary label="StockDetail"><StockDetailPage /></ErrorBoundary>} />
              <Route path="alpha-factory" element={<LazyRoute label="AlphaFactory"><AlphaFactoryPage /></LazyRoute>} />
              <Route path="signal-flag" element={<LazyRoute label="SignalFlag"><SignalFlagPage /></LazyRoute>} />

              {/* M1 — Core Flow Routes (14 pages) */}
              <Route path="portfolio" element={<LazyRoute label="Portfolio"><PortfolioPage /></LazyRoute>} />
              <Route path="portfolio/:id" element={<LazyRoute label="PortfolioDetail"><PortfolioDetailPage /></LazyRoute>} />
              <Route path="self-stocks" element={<LazyRoute label="SelfStocks"><SelfStocksPage /></LazyRoute>} />
              <Route path="hot-sectors" element={<LazyRoute label="HotSectors"><HotSectorsPage /></LazyRoute>} />
              <Route path="global-radar" element={<LazyRoute label="GlobalRadar"><GlobalRadarPage /></LazyRoute>} />
              <Route path="stock-selector" element={<LazyRoute label="StockSelector"><StockSelectorPage /></LazyRoute>} />
              <Route path="long-term-select" element={<LazyRoute label="LongTermSelect"><LongTermSelectPage /></LazyRoute>} />
              <Route path="strategy-compare" element={<LazyRoute label="StrategyCompare"><StrategyComparePage /></LazyRoute>} />
              <Route path="strategy-snapshots" element={<LazyRoute label="StrategySnapshots"><StrategySnapshotsPage /></LazyRoute>} />
              <Route path="decision-snapshot/:snapshotId" element={<LazyRoute label="DecisionSnapshot"><DecisionSnapshotPage /></LazyRoute>} />
              <Route path="share/decision/:shareToken" element={<LazyRoute label="DecisionSnapshotPublic"><DecisionSnapshotPublicPage /></LazyRoute>} />
              <Route path="nl-strategy" element={<LazyRoute label="NLStrategy"><NLStrategyPage /></LazyRoute>} />
              <Route path="strategy-wizard" element={<LazyRoute label="StrategyWizard"><StrategyWizardPage /></LazyRoute>} />
              <Route path="tdx-blocks" element={<LazyRoute label="TdxBlocks"><TdxBlocksPage /></LazyRoute>} />

              {/* M2 — Collaborative & Swarm Pages (10 pages) */}
              <Route path="collaboration-workspace" element={<LazyRoute label="CollaborationWorkspace"><CollaborationWorkspacePage /></LazyRoute>} />
              <Route path="message-center" element={<LazyRoute label="MessageCenter"><MessageCenterPage /></LazyRoute>} />
              <Route path="task-center" element={<LazyRoute label="TaskCenter"><TaskCenterPage /></LazyRoute>} />
              <Route path="task/:taskId" element={<LazyRoute label="TaskDetail"><TaskDetailPage /></LazyRoute>} />
              <Route path="swarm-dashboard" element={<LazyRoute label="SwarmDashboard"><SwarmDashboardPage /></LazyRoute>} />
              <Route path="swarm-designer" element={<LazyRoute label="SwarmDesigner"><SwarmDesignerPage /></LazyRoute>} />
              <Route path="signal-observations" element={<LazyRoute label="SignalObservations"><SignalObservationsPage /></LazyRoute>} />
              <Route path="voice-briefing" element={<LazyRoute label="VoiceBriefing"><VoiceBriefingPage /></LazyRoute>} />
              <Route path="research-canvas" element={<LazyRoute label="ResearchCanvas"><ResearchCanvasPage /></LazyRoute>} />
              <Route path="research-pipeline" element={<LazyRoute label="ResearchPipeline"><ResearchPipelinePage /></LazyRoute>} />

              {/* M2 — AI & Analytics Pages (8 pages) */}
              <Route path="ai-chat" element={<LazyRoute label="AIChat"><AIChatPage /></LazyRoute>} />
              <Route path="ai-analysis" element={<LazyRoute label="AIAnalysis"><AIAnalysisPage /></LazyRoute>} />
              <Route path="ai-research-report" element={<LazyRoute label="AIResearchReport"><AIResearchReportPage /></LazyRoute>} />
              <Route path="ai-hedge-fund" element={<LazyRoute label="AIHedgeFund"><AIHedgeFundPage /></LazyRoute>} />
              <Route path="ai-committee-dashboard" element={<LazyRoute label="AICommitteeDashboard"><AICommitteeDashboardPage /></LazyRoute>} />
              <Route path="ai-committee-selection" element={<LazyRoute label="AICommitteeSelection"><AICommitteeSelectionPage /></LazyRoute>} />
              <Route path="ai-investment-committee" element={<LazyRoute label="AIInvestmentCommittee"><AIInvestmentCommitteePage /></LazyRoute>} />
              <Route path="war-room" element={<LazyRoute label="WarRoom"><WarRoomPage /></LazyRoute>} />

              {/* M2 — Secondary Data Pages (9 pages) */}
              <Route path="alert-center" element={<LazyRoute label="AlertCenter"><AlertCenterPage /></LazyRoute>} />
              <Route path="yanbao-hub" element={<LazyRoute label="YanbaoHub"><YanbaoHubPage /></LazyRoute>} />
              <Route path="longhu-bang" element={<LazyRoute label="LonghuBang"><LonghuBangPage /></LazyRoute>} />
              <Route path="selection-result/:taskId" element={<LazyRoute label="SelectionResult"><SelectionResultPage /></LazyRoute>} />
              <Route path="investment-managers" element={<LazyRoute label="InvestmentManagers"><InvestmentManagersPage /></LazyRoute>} />
              <Route path="investment-managers/:managerId" element={<LazyRoute label="InvestmentManagerDetail"><InvestmentManagerDetailPage /></LazyRoute>} />
              <Route path="expert-teams" element={<LazyRoute label="ExpertTeams"><ExpertTeamsPage /></LazyRoute>} />
              <Route path="agent-center" element={<LazyRoute label="AgentCenter"><AgentCenterPage /></LazyRoute>} />
              <Route path="decision-replay" element={<LazyRoute label="DecisionReplaySpace"><DecisionReplaySpacePage /></LazyRoute>} />

              {/* Factor Pages */}
              <Route path="factor-repository" element={<LazyRoute label="FactorRepository"><FactorRepositoryPage /></LazyRoute>} />
              <Route path="factor-evolution" element={<LazyRoute label="FactorEvolution"><FactorEvolutionPage /></LazyRoute>} />
              <Route path="factor/:factorId" element={<LazyRoute label="FactorDetail"><FactorDetailPage /></LazyRoute>} />

              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
