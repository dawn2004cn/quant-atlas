import useSWR from "swr";
import { apiFetchV1 } from "../lib/api";

export type PersonaPayload = {
  tier?: string;
  risk_tolerance?: number;
  experience_score?: number;
  trading_frequency?: string;
  feature_mask?: Record<string, boolean>;
  assessed_at?: string;
};

export function usePersona() {
  const { data, error, isLoading } = useSWR(
    "user-persona",
    () => apiFetchV1<PersonaPayload>("/user/persona"),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  return {
    persona: data ?? null,
    featureMask: data?.feature_mask ?? {},
    loading: isLoading,
    error,
  };
}

/** Hide nav items tagged with personaFeature when mask explicitly disables them. */
export function isPersonaNavVisible(
  featureMask: Record<string, boolean>,
  personaFeature?: string,
): boolean {
  if (!personaFeature) return true;
  if (!(personaFeature in featureMask)) return true;
  return featureMask[personaFeature] !== false;
}
