/**
 * Switcher telemetry — Jinja page companion script.
 *
 * This lightweight script is included in Jinja templates via the `{% block spa_switcher %}`
 * block. It provides `window.trackSwitcherClick()` for onclick handlers on "试试新版 →" links.
 *
 * The SPA-side equivalent is `frontend/src/lib/switcher-telemetry.ts`, which also
 * provides `trackBackToClassic()` for the "回到经典版 ←" link.
 *
 * This script is intentionally plain JS (no build step) because Jinja pages don't
 * load the SPA bundle.
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
})();