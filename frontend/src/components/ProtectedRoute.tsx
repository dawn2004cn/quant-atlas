import { Navigate, Outlet, useLocation } from "react-router-dom";
import { PageSkeleton } from "./PageSkeleton";
import { useAuth } from "../hooks/useAuth";

export function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <PageSkeleton rows={4} />;
  }

  if (!isAuthenticated) {
    const redirectTo =
      location.pathname && location.pathname !== "/"
        ? `${location.pathname}${location.search}${location.hash}`
        : "/";
    return <Navigate to="/login" replace state={{ from: redirectTo }} />;
  }

  return <Outlet />;
}
