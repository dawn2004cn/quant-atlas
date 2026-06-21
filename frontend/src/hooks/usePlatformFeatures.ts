import useSWR from "swr";
import { apiFetch } from "../lib/api";

export type PlatformFeatures = {
  feature_war_room: boolean;
  feature_alpha_marketplace: boolean;
  feature_decision_theater: boolean;
  feature_swarm_topology: boolean;
  feature_federated_mesh: boolean;
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
