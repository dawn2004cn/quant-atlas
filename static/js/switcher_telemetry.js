/**
 * Switcher telemetry — Jinja page companion script.
 *
 * Loaded globally from base.html. Provides:
 *   1. window.trackSwitcherClick(page) — programmatic API (kept for backward compat)
 *   2. Delegated click listener on [data-spa-switcher] elements — CSP-safe alternative
 *      to inline onclick handlers.
 *
 * Templates should use:
 *   <a href="/app/foo" class="spa-switcher-link" data-spa-switcher="foo">试试新版 →</a>
 *
 * The SPA-side equivalent is `frontend/src/lib/switcher-telemetry.ts`, which also
 * provides `trackBackToClassic()` for the "回到经典版 ←" link.
 */

(function () {
  var ENDPOINT = "/api/v1/telemetry/switcher";

  function post(data) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", ENDPOINT, true);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(JSON.stringify(data));
    } catch (e) {
      // Fire-and-forget
    }
  }

  window.trackSwitcherClick = function (page) {
    post({ event: "switch_to_spa", page: page });
  };

  // Delegated listener — CSP-safe replacement for inline onclick handlers.
  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!target || typeof target.closest !== "function") return;
    var link = target.closest("[data-spa-switcher]");
    if (!link) return;
    var page = link.getAttribute("data-spa-switcher");
    if (page) post({ event: "switch_to_spa", page: page });
  });
})();
