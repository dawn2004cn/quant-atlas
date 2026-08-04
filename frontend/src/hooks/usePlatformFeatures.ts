import useSWR from "swr";
import { apiFetch } from "../lib/api";

export type PlatformFeatures = {
  feature_war_room: boolean;
  feature_alpha_marketplace: boolean;
  feature_decision_theater: boolean;
  feature_swarm_topology: boolean;
  feature_federated_mesh: boolean;
  nav_show_spa_shell?: boolean;
  nav_show_ai_hedge_fund?: boolean;
  nav_show_agent_center?: boolean;
  nav_show_voice_briefing?: boolean;
  nav_show_research_canvas?: boolean;
  nav_show_alpha_factory?: boolean;
  nav_show_data_lake_health?: boolean;
  nav_show_user_tiers?: boolean;
  nav_show_zen_terminal?: boolean;
  nav_show_integration_hub?: boolean;
  nav_show_observability?: boolean;
  nav_show_moments?: boolean;
  nav_show_investment_managers?: boolean;
  nav_show_collaboration_workspace?: boolean;
};

const DEFAULT_FEATURES: PlatformFeatures = {
  feature_war_room: false,
  feature_alpha_marketplace: false,
  feature_decision_theater: false,
  feature_swarm_topology: false,
  feature_federated_mesh: false,
};

export function usePlatformFeatures() {
  const { data, error, isLoading } = useSWR(
    "/api/v1/platform/strategic-features",
    (path) => apiFetch<PlatformFeatures>(path),
    { revalidateOnFocus: false },
  );

  return {
    features: data ?? DEFAULT_FEATURES,
    loading: isLoading,
    error,
  };
}

export function isNavItemVisible(
  features: Record<string, boolean | undefined>,
  navId?: string,
  strategicFeature?: string,
): boolean {
  if (strategicFeature && !features[strategicFeature]) {
    return false;
  }
  if (!navId) {
    return true;
  }
  const key = `nav_show_${navId}`;
  if (key in features) {
    return Boolean(features[key]);
  }
  return true;
}
