import type { ReactNode } from "react";
import type { PlatformFeatures } from "../hooks/usePlatformFeatures";
import { usePlatformFeatures } from "../hooks/usePlatformFeatures";
import { FeatureRetired } from "./FeatureRetired";
import { PageSkeleton } from "./PageSkeleton";

type FeatureKey = keyof PlatformFeatures;

type Props = {
  feature: FeatureKey;
  children: ReactNode;
};

export function FeatureGate({ feature, children }: Props) {
  const { features, loading } = usePlatformFeatures();

  if (loading) {
    return <PageSkeleton />;
  }
  if (!features[feature]) {
    return <FeatureRetired feature={feature} />;
  }
  return children;
}
