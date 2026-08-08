/**
 * Dismissible onboarding strips — persists per-page in localStorage.
 * Mark section with: data-ux-onboarding="page-id"
 */
(function () {
  function init() {
    document.querySelectorAll("[data-ux-onboarding]").forEach(function (el) {
      var key = "qc_ux_onboard_dismiss:" + el.getAttribute("data-ux-onboarding");
      if (localStorage.getItem(key) === "1") {
        el.classList.add("qa-is-hidden");
        return;
      }
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "qc-ux-onboarding-dismiss";
      btn.setAttribute("aria-label", "收起上手提示");
      btn.textContent = "知道了";
      btn.addEventListener("click", function () {
        localStorage.setItem(key, "1");
        el.classList.add("qa-is-hidden");
      });
      el.appendChild(btn);
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
