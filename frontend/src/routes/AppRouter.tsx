import { CircularProgress, Stack } from "@mui/material";
import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "../components/ProtectedRoute";
import { RoleRoute } from "../components/RoleRoute";

const AppLayout = lazy(() => import("../layouts/AppLayout").then((module) => ({ default: module.AppLayout })));
const LoginPage = lazy(() => import("../pages/LoginPage").then((module) => ({ default: module.LoginPage })));
const RegisterPage = lazy(() => import("../pages/RegisterPage").then((module) => ({ default: module.RegisterPage })));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })));
const ProductDashboardPage = lazy(() => import("../pages/ProductDashboardPage").then((module) => ({ default: module.ProductDashboardPage })));
const ProductGamesPage = lazy(() => import("../pages/ProductGamesPage").then((module) => ({ default: module.ProductGamesPage })));
const ProductGameDetailPage = lazy(() => import("../pages/ProductGameDetailPage").then((module) => ({ default: module.ProductGameDetailPage })));
const ProductPerformancePage = lazy(() => import("../pages/ProductPerformancePage").then((module) => ({ default: module.ProductPerformancePage })));
const ProductSavedPicksPage = lazy(() => import("../pages/ProductSavedPicksPage").then((module) => ({ default: module.ProductSavedPicksPage })));
const ProductProfilePage = lazy(() => import("../pages/ProductProfilePage").then((module) => ({ default: module.ProductProfilePage })));
const PredictionsPage = lazy(() => import("../pages/PredictionsPage").then((module) => ({ default: module.PredictionsPage })));
const TeamIntelligencePage = lazy(() => import("../pages/TeamIntelligencePage").then((module) => ({ default: module.TeamIntelligencePage })));
const AnalyticsPage = lazy(() => import("../pages/AnalyticsPage").then((module) => ({ default: module.AnalyticsPage })));
const ModelsPage = lazy(() => import("../pages/ModelsPage").then((module) => ({ default: module.ModelsPage })));
const ProductExperiencePage = lazy(() => import("../pages/ProductExperiencePage").then((module) => ({ default: module.ProductExperiencePage })));
const OnboardingPage = lazy(() => import("../pages/OnboardingPage").then((module) => ({ default: module.OnboardingPage })));
const AssistantPage = lazy(() => import("../../app/assistant/page").then((module) => ({ default: module.default })));
const CommunityPage = lazy(() => import("../../app/community/page").then((module) => ({ default: module.default })));
const CommunityFeedPage = lazy(() => import("../../app/community/feed/page").then((module) => ({ default: module.default })));
const CommunityLeaderboardPage = lazy(() => import("../../app/community/leaderboard/page").then((module) => ({ default: module.default })));
const CommunityProfilePage = lazy(() => import("../../app/community/profile/page").then((module) => ({ default: module.default })));
const CommunityStrategiesPage = lazy(() => import("../../app/community/strategies/page").then((module) => ({ default: module.default })));
const ResearchAgentPage = lazy(() => import("../../app/research-agent/page").then((module) => ({ default: module.default })));
const ResearchAgentProjectsPage = lazy(() => import("../../app/research-agent/projects/page").then((module) => ({ default: module.default })));
const ResearchAgentBacktestPage = lazy(() => import("../../app/research-agent/backtest/page").then((module) => ({ default: module.default })));
const ResearchAgentSimulatorPage = lazy(() => import("../../app/research-agent/simulator/page").then((module) => ({ default: module.default })));
const ResearchAgentReportsPage = lazy(() => import("../../app/research-agent/reports/page").then((module) => ({ default: module.default })));
const SimulatorPage = lazy(() => import("../../app/simulator/page").then((module) => ({ default: module.default })));
const PortfolioPage = lazy(() => import("../../app/portfolio/page").then((module) => ({ default: module.default })));
const ResearchPage = lazy(() => import("../../app/research/page").then((module) => ({ default: module.default })));
const SettingsPage = lazy(() => import("../../app/settings/page").then((module) => ({ default: module.default })));
const EnterprisePage = lazy(() => import("../../app/enterprise/page").then((module) => ({ default: module.default })));
const AILearningPage = lazy(() => import("../../app/ai-learning/page").then((module) => ({ default: module.default })));
const AIAgentPage = lazy(() => import("../../app/ai-agent/page").then((module) => ({ default: module.default })));
const AINetworkPage = lazy(() => import("../../app/ai-network/page").then((module) => ({ default: module.default })));
const AINetworkAgentsPage = lazy(() => import("../../app/ai-network/agents/page").then((module) => ({ default: module.default })));
const AINetworkDebatesPage = lazy(() => import("../../app/ai-network/debates/page").then((module) => ({ default: module.default })));
const AINetworkPerformancePage = lazy(() => import("../../app/ai-network/performance/page").then((module) => ({ default: module.default })));
const AINetworkDecisionsPage = lazy(() => import("../../app/ai-network/decisions/page").then((module) => ({ default: module.default })));
const AutonomousResearchPage = lazy(() => import("../../app/autonomous-research/page").then((module) => ({ default: module.default })));
const AutonomousResearchDiscoveryFeedPage = lazy(() => import("../../app/autonomous-research/discovery-feed/page").then((module) => ({ default: module.default })));
const AutonomousResearchActiveExperimentsPage = lazy(() => import("../../app/autonomous-research/active-experiments/page").then((module) => ({ default: module.default })));
const AutonomousResearchFindingsPage = lazy(() => import("../../app/autonomous-research/findings/page").then((module) => ({ default: module.default })));
const AutonomousResearchImprovementQueuePage = lazy(() => import("../../app/autonomous-research/improvement-queue/page").then((module) => ({ default: module.default })));
const AutonomousResearchKnowledgeGraphPage = lazy(() => import("../../app/autonomous-research/knowledge-graph/page").then((module) => ({ default: module.default })));
const SportsBrainPage = lazy(() => import("../../app/sports-brain/page").then((module) => ({ default: module.default })));
const SportsBrainAskAIPage = lazy(() => import("../../app/sports-brain/ask-ai/page").then((module) => ({ default: module.default })));
const SportsBrainKnowledgeMapPage = lazy(() => import("../../app/sports-brain/knowledge-map/page").then((module) => ({ default: module.default })));
const SportsBrainReasoningPage = lazy(() => import("../../app/sports-brain/reasoning/page").then((module) => ({ default: module.default })));
const SportsBrainResearchPage = lazy(() => import("../../app/sports-brain/research/page").then((module) => ({ default: module.default })));
const SportsBrainInsightsPage = lazy(() => import("../../app/sports-brain/insights/page").then((module) => ({ default: module.default })));
const SportsBrainHistoryPage = lazy(() => import("../../app/sports-brain/history/page").then((module) => ({ default: module.default })));
const AdminPipelinePage = lazy(() => import("../../app/admin/pipeline/page").then((module) => ({ default: module.default })));

function RouteLoader() {
  return (
    <Stack alignItems="center" justifyContent="center" minHeight="100vh">
      <CircularProgress color="secondary" />
    </Stack>
  );
}

export function AppRouter() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<ProductDashboardPage />} />
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/product" element={<ProductExperiencePage />} />
            <Route path="/product/live" element={<ProductExperiencePage />} />
            <Route path="/product/settings" element={<ProductExperiencePage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/profile" element={<ProductProfilePage />} />
            <Route path="/community" element={<CommunityPage />} />
            <Route path="/community/feed" element={<CommunityFeedPage />} />
            <Route path="/community/leaderboard" element={<CommunityLeaderboardPage />} />
            <Route path="/community/profile" element={<CommunityProfilePage />} />
            <Route path="/community/strategies" element={<CommunityStrategiesPage />} />
            <Route path="/research-agent" element={<ResearchAgentPage />} />
            <Route path="/research-agent/projects" element={<ResearchAgentProjectsPage />} />
            <Route path="/research-agent/backtest" element={<ResearchAgentBacktestPage />} />
            <Route path="/research-agent/simulator" element={<ResearchAgentSimulatorPage />} />
            <Route path="/research-agent/reports" element={<ResearchAgentReportsPage />} />
            <Route path="/simulator" element={<SimulatorPage />} />
            <Route path="/portfolio" element={<PortfolioPage />} />
            <Route path="/enterprise" element={<EnterprisePage />} />
            <Route path="/ai-learning" element={<AILearningPage />} />
            <Route path="/ai-agent" element={<AIAgentPage />} />
            <Route path="/network" element={<AINetworkPage />} />
            <Route path="/network/agents" element={<AINetworkAgentsPage />} />
            <Route path="/network/debates" element={<AINetworkDebatesPage />} />
            <Route path="/network/performance" element={<AINetworkPerformancePage />} />
            <Route path="/network/decisions" element={<AINetworkDecisionsPage />} />
            <Route path="/autonomous-research" element={<AutonomousResearchPage />} />
            <Route path="/autonomous-research/discovery-feed" element={<AutonomousResearchDiscoveryFeedPage />} />
            <Route path="/autonomous-research/active-experiments" element={<AutonomousResearchActiveExperimentsPage />} />
            <Route path="/autonomous-research/findings" element={<AutonomousResearchFindingsPage />} />
            <Route path="/autonomous-research/improvement-queue" element={<AutonomousResearchImprovementQueuePage />} />
            <Route path="/autonomous-research/knowledge-graph" element={<AutonomousResearchKnowledgeGraphPage />} />
            <Route path="/sports-brain" element={<SportsBrainPage />} />
            <Route path="/sports-brain/ask-ai" element={<SportsBrainAskAIPage />} />
            <Route path="/sports-brain/knowledge-map" element={<SportsBrainKnowledgeMapPage />} />
            <Route path="/sports-brain/reasoning" element={<SportsBrainReasoningPage />} />
            <Route path="/sports-brain/research" element={<SportsBrainResearchPage />} />
            <Route path="/sports-brain/insights" element={<SportsBrainInsightsPage />} />
            <Route path="/sports-brain/history" element={<SportsBrainHistoryPage />} />
            <Route path="/games" element={<ProductGamesPage />} />
            <Route path="/games/:gameId" element={<ProductGameDetailPage />} />
            <Route path="/performance" element={<ProductPerformancePage />} />
            <Route path="/saved-picks" element={<ProductSavedPicksPage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/teams" element={<TeamIntelligencePage />} />
            <Route path="/team-intelligence" element={<Navigate to="/teams" replace />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route element={<RoleRoute allowedRoles={["analyst", "admin"]} />}>
              <Route path="/predictions" element={<PredictionsPage />} />
              <Route path="/models" element={<ModelsPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={["admin"]} />}>
              <Route path="/admin/pipeline" element={<AdminPipelinePage />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
