/**
 * Shared Truth Badge fetch helper — single API path for all consumers.
 */
(function (global) {
    'use strict';

    function unwrap(json) {
        if (global.QCApi && global.QCApi.unwrap) {
            return global.QCApi.unwrap(json);
        }
        if (json && json.data !== undefined) return json.data;
        return json;
    }

    /**
     * @param {string} symbol
     * @param {string} [market]
     * @returns {Promise<object|null>}
     */
    async function loadTruthBadge(symbol, market) {
        var m = (market || 'CN').toUpperCase();
        var sym = String(symbol || '').trim();
        if (!sym) return null;
        var path = '/truth/badge/' + encodeURIComponent(m) + '/' + encodeURIComponent(sym);
        try {
            if (global.QCApi) {
                return await global.QCApi.get(path);
            }
            var res = await fetch('/api/v1' + path, { credentials: 'same-origin' });
            if (!res.ok) return null;
            return unwrap(await res.json());
        } catch (err) {
            if (typeof global.qcLogError === 'function') {
                global.qcLogError('truth_badge.load failed', err);
            }
            return null;
        }
    }

    global.QCTruthBadge = {
        load: loadTruthBadge,
    };
})(window);
