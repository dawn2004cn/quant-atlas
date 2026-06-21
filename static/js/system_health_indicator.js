(function (global) {
    'use strict';

    var POLL_MS = 60000;
    var timer = null;

    function applyLevel(el, dot, banner, level, message) {
        var cls = level === 'critical' ? 'critical' : level === 'warning' ? 'warning' : 'ok';
        el.className = 'qc-health-indicator qc-health-indicator--' + cls;
        dot.className = 'qc-health-dot qc-health-dot--' + cls;
        el.title = message || '系统健康';
        if (banner) {
            banner.className = 'qc-global-health-banner qc-global-health-banner--' + cls + (level === 'ok' ? ' qa-is-hidden' : '');
            banner.querySelector('.qc-global-health-banner__msg').textContent = message || '';
        }
    }

    async function refresh() {
        var el = document.getElementById('qcHealthIndicator');
        var dot = document.getElementById('qcHealthDot');
        var banner = document.getElementById('qcGlobalHealthBanner');
        if (!el || !dot) return;
        try {
            var res = await fetch('/api/v1/system/health-banner');
            if (!res.ok) throw new Error('HTTP ' + res.status);
            var body = await res.json();
            var data = body.data !== undefined ? body.data : body;
            applyLevel(el, dot, banner, data.level || 'ok', data.message || '');
        } catch (e) {
            applyLevel(el, dot, banner, 'warning', '健康状态暂不可用');
        }
    }

    function start() {
        if (timer) clearInterval(timer);
        refresh();
        timer = setInterval(refresh, POLL_MS);
    }

    global.QCSystemHealth = { refresh: refresh, start: start };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})(window);
