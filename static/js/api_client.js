/**
 * Unified API client for Quant Atlas frontend.
 *
 * Replaces scattered $.getJSON / fetch() calls with a single
 * authenticated, error-normalized entrypoint.
 */
(function (global) {
    'use strict';

    var DEFAULTS = {
        baseUrl: '/api/v1',
        credentials: 'same-origin',
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        },
    };

    /**
     * Show a toast error for API failures.
     * Debounces rapid errors to avoid toast spam.
     */
    var lastToastTime = 0;
    var TOAST_COOLDOWN = 2000; // ms

    function showToastError(msg) {
        var now = Date.now();
        if (now - lastToastTime < TOAST_COOLDOWN) return;
        lastToastTime = now;
        if (typeof window.showToast === 'function') {
            window.showToast(msg, 'error', 5000);
        }
    }

    function unwrap(json) {
        if (!json || typeof json !== 'object') return json;
        if ((json.success === true || json.ok === true || json.status === 'success') && json.data !== undefined) {
            return json.data;
        }
        return json;
    }

    /**
     * @param {string} path - API path (without /api/v1 prefix)
     * @param {object} [options]
     * @returns {Promise<any>}
     */
    function api(path, options) {
        options = options || {};
        var url = DEFAULTS.baseUrl + path;
        var method = (options.method || 'GET').toUpperCase();
        var headers = Object.assign({}, DEFAULTS.headers, options.headers || {});
        if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
            if (typeof window.getCsrfToken === 'function') {
                var token = window.getCsrfToken();
                if (token && !headers['X-CSRF-Token'] && !headers['X-CSRFToken']) {
                    headers['X-CSRFToken'] = token;
                    headers['X-CSRF-Token'] = token;
                }
            }
        }
        var fetchOpts = Object.assign({}, options, {
            credentials: DEFAULTS.credentials,
            headers: headers,
        });
        if (fetchOpts.body && typeof fetchOpts.body === 'object' && !(fetchOpts.body instanceof FormData)) {
            fetchOpts.body = JSON.stringify(fetchOpts.body);
            fetchOpts.headers['Content-Type'] = 'application/json';
        }
        return fetch(url, fetchOpts)
            .then(function (res) {
                if (!res.ok) {
                    return res.json().then(function (err) {
                        var msg = (err && err.error && err.error.message) || err && err.message || ('HTTP ' + res.status);
                        showToastError(msg);
                        throw new Error(msg);
                    }).catch(function () {
                        return res.text().then(function (txt) {
                            showToastError(txt || ('HTTP ' + res.status));
                            throw new Error(txt || ('HTTP ' + res.status));
                        });
                    });
                }
                if (res.status === 204) return null;
                return res.json().then(unwrap);
            });
    }

    global.QCApi = {
        get: function (path) { return api(path, { method: 'GET' }); },
        post: function (path, body) { return api(path, { method: 'POST', body: body }); },
        put: function (path, body) { return api(path, { method: 'PUT', body: body }); },
        delete: function (path) { return api(path, { method: 'DELETE' }); },
        raw: api,
        unwrap: unwrap,
    };

})(window);
