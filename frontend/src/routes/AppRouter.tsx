import { CircularProgress, Stack } from "@mui/material";
import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "../components/ProtectedRoute";
import { AdminRoute } from "../components/AdminRoute";
import { PremiumRoute } from "../components/PremiumRoute";

const AppLayout = lazy(() => import("../layouts/AppLayout").then((module) => ({ default: module.AppLayout })));
const PublicLayout = lazy(() => import("../layouts/PublicLayout").then((module) => ({ default: module.PublicLayout })));
const LandingPage = lazy(() => import("../pages/LandingPage").then((module) => ({ default: module.LandingPage })));
const LegalPage = lazy(() => import("../pages/LegalPage").then((module) => ({ default: module.LegalPage })));
const FreePreviewPage = lazy(() => import("../pages/FreePreviewPage").then((module) => ({ default: module.FreePreviewPage })));
const LoginPage = lazy(() => import("../pages/LoginPage").then((module) => ({ default: module.LoginPage })));
const RegisterPage = lazy(() => import("../pages/RegisterPage").then((module) => ({ default: module.RegisterPage })));
const ForgotPasswordPage = lazy(() => import("../pages/ForgotPasswordPage").then((module) => ({ default: module.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import("../pages/ResetPasswordPage").then((module) => ({ default: module.ResetPasswordPage })));
const ForgotEmailPage = lazy(() => import("../pages/ForgotEmailPage").then((module) => ({ default: module.ForgotEmailPage })));
const VerifyEmailPage = lazy(() => import("../pages/VerifyEmailPage").then((module) => ({ default: module.VerifyEmailPage })));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })));
const ProductDashboardPage = lazy(() => import("../pages/ProductDashboardPage").then((module) => ({ default: module.ProductDashboardPage })));
const ProductGamesPage = lazy(() => import("../pages/ProductGamesPage").then((module) => ({ default: module.ProductGamesPage })));
const ProductGameDetailPage = lazy(() => import("../pages/ProductGameDetailPage").then((module) => ({ default: module.ProductGameDetailPage })));
const ProductPerformancePage = lazy(() => import("../pages/ProductPerformancePage").then((module) => ({ default: module.ProductPerformancePage })));
const ProductSavedPicksPage = lazy(() => import("../pages/ProductSavedPicksPage").then((module) => ({ default: module.ProductSavedPicksPage })));
const ProductProfilePage = lazy(() => import("../pages/ProductProfilePage").then((module) => ({ default: module.ProductProfilePage })));
const ParlayOptimizerPage = lazy(() => import("../pages/ParlayOptimizerPage").then((module) => ({ default: module.ParlayOptimizerPage })));
const HowItWorksPage = lazy(() => import("../pages/HowItWorksPage").then((module) => ({ default: module.HowItWorksPage })));
const WorkerHealthPage = lazy(() => import("../pages/WorkerHealthPage").then((module) => ({ default: module.WorkerHealthPage })));

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
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/forgot-email" element={<ForgotEmailPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/how-it-works" element={<HowItWorksPage />} />
          {["terms", "privacy", "responsible-gaming", "disclaimer", "support"].map((path) => (
            <Route key={path} path={`/${path}`} element={<LegalPage />} />
          ))}
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<PremiumRoute preview={<FreePreviewPage />}><ProductDashboardPage /></PremiumRoute>} />
            <Route path="/product/*" element={<Navigate to="/dashboard" replace />} />
            <Route path="/profile" element={<ProductProfilePage />} />
            <Route element={<PremiumRoute />}>
              <Route path="/games" element={<ProductGamesPage />} />
              <Route path="/games/:gameId" element={<ProductGameDetailPage />} />
              <Route path="/performance" element={<ProductPerformancePage />} />
              <Route path="/saved-picks" element={<ProductSavedPicksPage />} />
              <Route path="/parlays" element={<ParlayOptimizerPage />} />
            </Route>
            <Route element={<AdminRoute />}>
              <Route path="/admin/workers" element={<WorkerHealthPage />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
