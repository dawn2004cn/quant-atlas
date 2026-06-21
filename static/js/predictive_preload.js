(function (global) {
    'use strict';

    var seen = {};

    function idle(fn) {
        if (typeof global.requestIdleCallback === 'function') {
            global.requestIdleCallback(fn, { timeout: 2500 });
        } else {
            global.setTimeout(fn, 250);
        }
    }

    async function loadPlan(sectorCode, options) {
        var opts = options || {};
        var url = '/api/v1/hot-sectors/' + encodeURIComponent(sectorCode) + '/preload-plan';
        var params = new URLSearchParams();
        ['market', 'source', 'name', 'kind', 'provider', 'limit'].forEach(function (key) {
            if (opts[key] != null && opts[key] !== '') params.set(key, opts[key]);
        });
        var query = params.toString();
        if (query) url += '?' + query;
        var res = await fetch(url, { credentials: 'include' });
        var json = await res.json();
        if (!res.ok) throw new Error(((json.error || {}).message) || 'preload plan failed');
        return json.data || {};
    }

    function prefetch(plan) {
        var entries = plan.prefetch || [];
        var maxParallel = ((plan.policy || {}).max_parallel) || 2;
        var queue = [];
        entries.forEach(function (entry) {
            (entry.urls || []).forEach(function (url) {
                if (!seen[url]) queue.push(url);
            });
        });
        var active = 0;
        function pump() {
            while (active < maxParallel && queue.length) {
                var url = queue.shift();
                seen[url] = true;
                active += 1;
                fetch(url, { credentials: 'include' })
                    .catch(function () {})
                    .finally(function () {
                        active -= 1;
                        pump();
                    });
            }
        }
        idle(pump);
    }

    async function warmSector(sectorCode, options) {
        var plan = await loadPlan(sectorCode, options);
        prefetch(plan);
        return plan;
    }

    global.QAPredictivePreload = {
        loadPlan: loadPlan,
        prefetch: prefetch,
        warmSector: warmSector
    };
})(window);
