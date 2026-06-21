/**
 * QCStateBus — lightweight global state via CustomEvent + localStorage.
 *
 * Features:
 *  - subscribe / unsubscribe / publish
 *  - hydrate from server-rendered initial state
 *  - optional persistence to localStorage per key
 *  - debug mode (window.QC_DEBUG_STATE = true)
 *
 * Usage:
 *  QCStateBus.subscribe('user.preferences', function (state) { ... });
 *  QCStateBus.publish('user.preferences', { theme: 'dark' });
 *  QCStateBus.hydrate({ 'user.preferences': { theme: 'light' } });
 */
(function (global) {
    'use strict';

    var STORE_PREFIX = 'qa_state_';
    var DEBUG_KEY = 'QC_DEBUG_STATE';
    var listeners = {};
    var persisted = {};

    function isDebug() {
        try {
            return global[DEBUG_KEY] === true;
        } catch (e) {
            return false;
        }
    }

    function log() {
        if (!isDebug()) return;
        try {
            global.console.debug.apply(global.console, ['[QCStateBus]'].concat(Array.prototype.slice.call(arguments)));
        } catch (e) {
            /* ignore */
        }
    }

    function storageKey(key) {
        return STORE_PREFIX + String(key || '').replace(/[^a-zA-Z0-9_.-]/g, '_');
    }

    function readPersisted(key) {
        try {
            var raw = global.localStorage.getItem(storageKey(key));
            return raw ? JSON.parse(raw) : undefined;
        } catch (e) {
            return undefined;
        }
    }

    function writePersisted(key, value) {
        try {
            global.localStorage.setItem(storageKey(key), JSON.stringify(value));
        } catch (e) {
            /* ignore quota errors */
        }
    }

    function notify(key, value, prev) {
        var cbs = listeners[key] || [];
        cbs.forEach(function (cb) {
            try {
                if (typeof cb === 'function') cb(value, prev);
            } catch (e) {
                try { global.console.error('[QCStateBus] listener error', e); } catch (_) {}
            }
        });
        log('publish', key, { from: prev, to: value });
    }

    var QCStateBus = {
        subscribe: function (key, callback) {
            if (!key || typeof callback !== 'function') return function () {};
            if (!listeners[key]) listeners[key] = [];
            listeners[key].push(callback);
            log('subscribe', key, 'listeners=', listeners[key].length);
            return function () {
                QCStateBus.unsubscribe(key, callback);
            };
        },

        unsubscribe: function (key, callback) {
            if (!listeners[key]) return;
            listeners[key] = listeners[key].filter(function (fn) { return fn !== callback; });
            log('unsubscribe', key, 'listeners=', listeners[key].length);
        },

        publish: function (key, value, opts) {
            opts = opts || {};
            var prev = persisted[key];
            persisted[key] = value;
            if (opts.persist !== false) {
                writePersisted(key, value);
            }
            notify(key, value, prev);
        },

        getState: function (key) {
            if (Object.prototype.hasOwnProperty.call(persisted, key)) {
                return persisted[key];
            }
            var initial = readPersisted(key);
            if (typeof initial !== 'undefined') {
                persisted[key] = initial;
            }
            return initial;
        },

        hydrate: function (initialState) {
            if (!initialState || typeof initialState !== 'object') return;
            Object.keys(initialState).forEach(function (key) {
                persisted[key] = initialState[key];
                log('hydrate', key);
            });
            // Notify fresh listeners once after hydration.
            Object.keys(initialState).forEach(function (key) {
                notify(key, persisted[key], undefined);
            });
        },

        reset: function (key) {
            if (key) {
                delete persisted[key];
                try { global.localStorage.removeItem(storageKey(key)); } catch (e) {}
                return;
            }
            persisted = {};
            try {
                Object.keys(global.localStorage).forEach(function (k) {
                    if (k.indexOf(STORE_PREFIX) === 0) global.localStorage.removeItem(k);
                });
            } catch (e) {}
            log('reset all');
        },
    };

    global.QCStateBus = QCStateBus;
})(window);
