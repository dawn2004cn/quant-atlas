import { Navigate, Outlet, useLocation } from "react-router-dom";
import { hasCompletedOnboarding } from "../lib/onboarding";

/** Redirect authenticated users to persona onboarding once per browser. */
export function OnboardingGate() {
  const location = useLocation();
  const path = location.pathname.replace(/\/+$/, "") || "/";
  const onOnboarding = path === "/onboarding" || path.endsWith("/onboarding");

  if (!onOnboarding && !hasCompletedOnboarding()) {
    return <Navigate to="/onboarding" replace />;
  }

  return <Outlet />;
}
