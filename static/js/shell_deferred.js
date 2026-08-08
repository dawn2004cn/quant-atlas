/**
 * shell_deferred.js — Idle-load non-critical shell scripts after first paint.
 */
(function (global) {
    'use strict';

    function idle(fn) {
        if (typeof global.requestIdleCallback === 'function') {
            global.requestIdleCallback(fn, { timeout: 3500 });
        } else {
            global.setTimeout(fn, 300);
        }
    }

    function loadScript(url, onDone) {
        var el = document.createElement('script');
        el.src = url;
        el.defer = true;
        el.onload = function () {
            if (onDone) onDone();
        };
        el.onerror = function () {
            if (onDone) onDone();
        };
        document.body.appendChild(el);
    }

    function loadSequential(urls, index) {
        if (index >= urls.length) {
            return;
        }
        loadScript(urls[index], function () {
            loadSequential(urls, index + 1);
        });
    }

    function boot() {
        var tag = document.getElementById('shellDeferredConfig');
        if (!tag) {
            return;
        }
        var urls = [];
        try {
            urls = JSON.parse(tag.textContent || '[]');
        } catch (_err) {
            return;
        }
        if (!urls.length) {
            return;
        }
        loadSequential(urls, 0);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            idle(boot);
        });
    } else {
        idle(boot);
    }
}(window));
