/**
 * Switcher telemetry SDK — fire-and-forget tracking for Flask↔SPA migration.
 *
 * Exposes `trackSwitcherClick` and `trackBackToClassic` for use in React code,
 * and `window.trackSwitcherClick` for Jinja onclick handlers.
 */

const TELEMETRY_ENDPOINT = "/api/v1/telemetry/switcher";

/**
 * Track a user clicking "试试新版 →" on the Flask page to switch to SPA.
 */
export function trackSwitcherClick(page: string): void {
  _post({ event: "switch_to_spa", page });
}

/**
 * Track a user clicking "回到经典版 ←" on the SPA page to go back to Flask.
 */
export function trackBackToClassic(page: string): void {
  _post({ event: "back_to_classic", page });
}

async function _post(payload: { event: string; page: string; user_id?: string | null }): Promise<void> {
  try {
    await fetch(TELEMETRY_ENDPOINT, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    // 204 = success, we don't need the response body
  } catch {
    // Fire-and-forget: silently ignore network errors
  }
}

// Expose on window for Jinja template onclick handlers
declare global {
  interface Window {
    trackSwitcherClick?: (page: string) => void;
  }
}

window.trackSwitcherClick = trackSwitcherClick;