"""Data Truth Dashboard — Phase 17 site-wide data hygiene frontend component."""

/**
 * QADataHygiene — Global Data Truth Dashboard widget.
 * Fetches /api/v1/provenance/truth-dashboard and renders a real-time
 * health bar with source confidence breakdown.
 */
(function (global) {
    "use strict";

    var POLL_MS = 30000;
    var _timer = null;

    function render(container, data) {
        if (!container || !data) return;

        var idx = data.global_truth_index || 0;
        var pct = (idx * 100).toFixed(0);
        var color = idx >= 0.85 ? "#198754" : idx >= 0.6 ? "#ffc107" : "#dc3545";

        container.innerHTML =
            '<div style="display:flex;align-items:center;gap:12px;padding:8px 12px;' +
            'border-radius:8px;background:var(--surface,rgba(0,0,0,.03));border:1px solid var(--surface-border,rgba(0,0,0,.08));">' +
            '<div style="flex:1;">' +
            '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">' +
            '<span style="font-weight:600;">\u6570\u636E\u771F\u76F8\u5EA6</span>' +
            '<span style="color:' + color + ';font-weight:700;">' + pct + '%</span>' +
            "</div>" +
            '<div style="height:6px;border-radius:3px;background:rgba(0,0,0,.06);overflow:hidden;">' +
            '<div style="height:100%;width:' + pct + '%;border-radius:3px;background:' + color + ";transition:width .5s ease;\"></div>" +
            "</div>" +
            '<div style="display:flex;gap:12px;margin-top:6px;font-size:10px;opacity:.6;">' +
            (data.sources || []).map(function (s) {
                return '<span style="color:' + s.color + ';">' + s.source + ": " + (s.health * 100).toFixed(0) + "%</span>";
            }).join("") +
            "</div>" +
            "</div>" +
            '<div style="font-size:10px;opacity:.4;white-space:nowrap;">\u5B9E\u65F6</div>' +
            "</div>";
    }

    async function refresh() {
        try {
            var res = await fetch("/api/v1/provenance/truth-dashboard");
            if (!res.ok) throw new Error("HTTP " + res.status);
            var body = await res.json();
            var data = body.data || body;

            var el = document.getElementById("qcDataHygieneBar");
            if (el) render(el, data);

            // Also publish to QCStateBus
            if (global.QCStateBus) {
                global.QCStateBus.publish("data.hygiene", data, { persist: false });
            }
        } catch (_) {
            // Keep last known state
        }
    }

    function start() {
        if (_timer) clearInterval(_timer);
        refresh();
        _timer = setInterval(refresh, POLL_MS);
    }

    global.QADataHygiene = { refresh: refresh, start: start };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})(window);
