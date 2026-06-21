/* Agent-App micro frontend prototype — Da Ban Radar (打板雷达) as installable card.
 * Drop this into any page to render a real-time limit-up monitoring widget. */

function initDaBanRadar(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;

    // Inject template
    container.innerHTML =
        '<div style="border:1px solid var(--surface-border,rgba(0,0,0,.1));border-radius:12px;' +
        'overflow:hidden;background:var(--surface,#fff);box-shadow:0 2px 8px rgba(0,0,0,.04);">' +
        '<div style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center;' +
        'background:linear-gradient(135deg,#c23616,#e74c3c);color:#fff;">' +
        '<span style="font-weight:700;font-size:14px;">⚡ 打板雷达</span>' +
        '<span style="font-size:11px;opacity:.7;">Kernel 级</span>' +
        "</div>" +
        '<div style="padding:12px 16px;">' +
        '<div id="dbrStockList" style="display:flex;flex-direction:column;gap:6px;">' +
        '<div style="text-align:center;padding:20px 0;color:var(--muted,#999);font-size:12px;">⏳ 加载中...</div>' +
        "</div>" +
        '<div style="margin-top:8px;text-align:right;">' +
        '<button type="button" data-dbr-action="refresh" style="background:var(--surface-strong,rgba(0,0,0,.05));' +
        'border:1px solid var(--surface-border,rgba(0,0,0,.1));border-radius:6px;padding:4px 12px;' +
        'font-size:11px;cursor:pointer;">🔄 刷新</button>' +
        "</div>" +
        "</div>" +
        "</div>";

    var refreshBtn = container.querySelector('[data-dbr-action="refresh"]');
    if (refreshBtn) refreshBtn.addEventListener('click', function () { global.dbrRefresh(); });

    // Mock refresh
    global.dbrRefresh = function () {
        var list = document.getElementById("dbrStockList");
        if (!list) return;
        list.innerHTML =
            '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(0,0,0,.04);">' +
            '<span style="font-weight:600;color:#c23616;">600519</span>' +
            '<span style="color:#c23616;">+10.00%</span>' +
            '<span style="font-size:11px;color:var(--muted,#999);">封单 2.3亿</span>' +
            "</div>" +
            '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(0,0,0,.04);">' +
            '<span style="font-weight:600;color:#c23616;">000858</span>' +
            '<span style="color:#c23616;">+9.98%</span>' +
            '<span style="font-size:11px;color:var(--muted,#999);">封单 1.8亿</span>' +
            "</div>" +
            '<div style="display:flex;justify-content:space-between;padding:6px 0;">' +
            '<span style="font-weight:600;color:#c23616;">300750</span>' +
            '<span style="color:#e67e22;">+8.52%</span>' +
            '<span style="font-size:11px;color:var(--muted,#999);">炸板中</span>" +
            "</div>";
    };

    global.dbrRefresh();
}

// Register as an installable Agent-App card
global.QuantumAgentApps = global.QuantumAgentApps || {};
global.QuantumAgentApps["da_ban_radar"] = {
    name: "打板雷达",
    icon: "zap",
    privilege: "Kernel",
    init: initDaBanRadar,
};
