/** Client-side onboarding gate (persona quiz). Backend persona is in-memory and resets on restart. */

const STORAGE_KEY = "qa_persona_onboarding_v1";

export function hasCompletedOnboarding(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function markOnboardingCompleted(): void {
  try {
    localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    // private mode / quota — gate will reappear next visit
  }
}

export function resetOnboardingFlag(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
