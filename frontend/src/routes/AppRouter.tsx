import { CircularProgress, Stack } from "@mui/material";
import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "../components/ProtectedRoute";

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
            <Route path="/product/*" element={<Navigate to="/dashboard" replace />} />
            <Route path="/profile" element={<ProductProfilePage />} />
            <Route path="/games" element={<ProductGamesPage />} />
            <Route path="/games/:gameId" element={<ProductGameDetailPage />} />
            <Route path="/performance" element={<ProductPerformancePage />} />
            <Route path="/saved-picks" element={<ProductSavedPicksPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}
