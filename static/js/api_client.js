/**
 * Unified API client for Quant Atlas frontend.
 *
 * Replaces scattered fetch() calls with authenticated, error-normalized requests.
 * 404 → toast「接口未注册」+ console 上报路径，便于排查路由契约漂移。
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

    var lastToastTime = 0;
    var TOAST_COOLDOWN = 2000;
    /** @type {Record<string, Promise<any>>} */
    var inflightRequests = {};

    function inflightKey(method, url, body) {
        var bodyPart = (typeof body === 'string') ? body : '';
        return method.toUpperCase() + ' ' + url + ' ' + bodyPart;
    }

    /** Identical in-flight GET/HEAD + identical POST/PUT/PATCH (same URL+body) share one fetch. */
    function coalescedFetch(url, fetchOpts) {
        var method = (fetchOpts.method || 'GET').toUpperCase();
        var body = fetchOpts.body;
        if (method !== 'GET' && method !== 'HEAD' && method !== 'POST' && method !== 'PUT' && method !== 'PATCH') {
            return fetch(url, fetchOpts);
        }
        if (body != null && typeof body !== 'string') {
            return fetch(url, fetchOpts);
        }
        var key = inflightKey(method, url, body);
        if (inflightRequests[key]) {
            return inflightRequests[key];
        }
        var pending = fetch(url, fetchOpts).finally(function () {
            if (inflightRequests[key] === pending) {
                delete inflightRequests[key];
            }
        });
        inflightRequests[key] = pending;
        return pending;
    }

    function showToastError(msg) {
        var now = Date.now();
        if (now - lastToastTime < TOAST_COOLDOWN) return;
        lastToastTime = now;
        if (typeof global.showToast === 'function') {
            global.showToast(msg, 'error', 5000);
        }
    }

    function unwrap(json) {
        if (!json || typeof json !== 'object') return json;
        if ((json.success === true || json.ok === true || json.status === 'success') && json.data !== undefined) {
            return json.data;
        }
        return json;
    }

    function resolveUrl(path) {
        if (!path) return DEFAULTS.baseUrl;
        if (path.indexOf('http://') === 0 || path.indexOf('https://') === 0) return path;
        if (path.indexOf('/api/') === 0) return path;
        var segment = path.charAt(0) === '/' ? path : '/' + path;
        return DEFAULTS.baseUrl + segment;
    }

    function errorMessage(res, errBody) {
        if (res.status === 404) {
            return '接口未注册或暂时不可用，请稍后重试或联系管理员';
        }
        if (res.status === 401) {
            return '请先登录后再操作';
        }
        if (res.status === 403) {
            return '没有权限执行此操作';
        }
        var body = errBody || {};
        return (body.error && body.error.message) || body.message || ('HTTP ' + res.status);
    }

    function reportFailure(res, msg) {
        if (res.status === 404) {
            console.warn('[QCApi] 404 route missing:', res.url || '');
        } else if (res.status >= 500) {
            console.warn('[QCApi] server error:', res.status, res.url || '');
        }
        showToastError(msg);
    }

    /**
     * @param {string} path - API path (with or without /api/v1 prefix)
     * @param {object} [options]
     * @returns {Promise<any>} unwrapped data
     */
    function api(path, options) {
        options = options || {};
        var url = resolveUrl(path);
        var method = (options.method || 'GET').toUpperCase();
        var headers = Object.assign({}, DEFAULTS.headers, options.headers || {});
        if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
            if (typeof global.getCsrfToken === 'function') {
                var token = global.getCsrfToken();
                if (token && !headers['X-CSRF-Token'] && !headers['X-CSRFToken']) {
                    headers['X-CSRFToken'] = token;
                    headers['X-CSRF-Token'] = token;
                }
            }
        }
        var fetchOpts = Object.assign({}, options, {
            credentials: options.credentials || DEFAULTS.credentials,
            headers: headers,
        });
        if (fetchOpts.body && typeof fetchOpts.body === 'object' && !(fetchOpts.body instanceof FormData)) {
            fetchOpts.body = JSON.stringify(fetchOpts.body);
            fetchOpts.headers['Content-Type'] = 'application/json';
        }
        return coalescedFetch(url, fetchOpts).then(function (res) {
            if (res.status === 204) return null;
            return res.json().catch(function () { return {}; }).then(function (json) {
                if (!res.ok) {
                    var msg = errorMessage(res, json);
                    reportFailure(res, msg);
                    var err = new Error(msg);
                    err.status = res.status;
                    err.url = res.url;
                    throw err;
                }
                return unwrap(json);
            });
        });
    }

    /**
     * Like api() but returns { ok, status, data, raw } for templates that need full envelope.
     */
    function fetchJson(path, options) {
        options = options || {};
        var url = resolveUrl(path);
        var method = (options.method || 'GET').toUpperCase();
        var headers = Object.assign({}, DEFAULTS.headers, options.headers || {});
        var fetchOpts = Object.assign({}, options, {
            method: method,
            credentials: options.credentials || DEFAULTS.credentials,
            headers: headers,
        });
        if (fetchOpts.body && typeof fetchOpts.body === 'object' && !(fetchOpts.body instanceof FormData)) {
            fetchOpts.body = JSON.stringify(fetchOpts.body);
            fetchOpts.headers['Content-Type'] = 'application/json';
        }
        return coalescedFetch(url, fetchOpts).then(function (res) {
            return res.json().catch(function () { return {}; }).then(function (json) {
                if (!res.ok) {
                    var msg = errorMessage(res, json);
                    reportFailure(res, msg);
                    var err = new Error(msg);
                    err.status = res.status;
                    err.url = res.url;
                    throw err;
                }
                return {
                    ok: true,
                    status: res.status,
                    data: unwrap(json),
                    raw: json,
                };
            });
        });
    }

    global.QCApi = {
        get: function (path) { return api(path, { method: 'GET' }); },
        post: function (path, body) { return api(path, { method: 'POST', body: body }); },
        put: function (path, body) { return api(path, { method: 'PUT', body: body }); },
        delete: function (path) { return api(path, { method: 'DELETE' }); },
        raw: api,
        fetchJson: fetchJson,
        unwrap: unwrap,
        resolveUrl: resolveUrl,
    };

})(window);
