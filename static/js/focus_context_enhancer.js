/**
 * focus_context_enhancer.js
 *
 * Opt-in page data refresh when global focus (symbol/market) changes.
 *
 * Usage:
 *   1. Add data-qa-focus-refresh="auto" to <body>
 *      -> page auto-refreshes via fetch(location.href) on focus change.
 *   2. Or override window.QA_REFRESH_ON_FOCUS_CHANGE = function(focus) { ... }
 *   3. Or respond to CustomEvent 'qa:focus-change' manually.
 */
(function (global) {
    'use strict';

    var READY = 'qa:focus-ready';

    function isAutoRefresh() {
        try {
            return (global.document.body && global.document.body.getAttribute('data-qa-focus-refresh') === 'auto');
        } catch (e) {
            return false;
        }
    }

    function autoRefresh(focus) {
        if (!focus || !focus.symbol) return;
        if (!isAutoRefresh()) return;
        try {
            var url = new URL(global.location.href);
            var mustUpdate = false;
            ['symbol', 'market', 'm'].forEach(function (key) {
                var val = url.searchParams.get(key);
                if (val && val !== '' + focus[key]) mustUpdate = true;
            });
            if (mustUpdate) {
                global.location.reload();
            }
        } catch (e) {
            /* ignore */
        }
    }

    function init() {
        if (global.document.documentElement.getAttribute(READY) === '1') return;
        global.document.documentElement.setAttribute(READY, '1');

        if (!global.QAFocusContext) return;

        if (isAutoRefresh()) {
            global.document.addEventListener('qa:focus-change', function (e) {
                if (e && e.detail) autoRefresh(e.detail);
            });
        }

        if (typeof global.QA_REFRESH_ON_FOCUS_CHANGE === 'function') {
            global.document.addEventListener('qa:focus-change', function (e) {
                if (e && e.detail) global.QA_REFRESH_ON_FOCUS_CHANGE(e.detail);
            });
        }
    }

    if (global.document.readyState === 'loading') {
        global.document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window);
