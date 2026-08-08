/**
 * lazy_three_legacy.js — Load legacy global THREE + OrbitControls on demand.
 */
(function (global) {
    'use strict';

    var pending = null;

    function readConfig() {
        var tag = document.getElementById('lazyThreeConfig');
        if (!tag) {
            return {};
        }
        try {
            return JSON.parse(tag.textContent || '{}');
        } catch (_err) {
            return {};
        }
    }

    function loadScript(src) {
        return new Promise(function (resolve, reject) {
            var el = document.createElement('script');
            el.src = src;
            el.onload = resolve;
            el.onerror = function () {
                reject(new Error('Failed to load ' + src));
            };
            document.head.appendChild(el);
        });
    }

    global.loadThreeLegacy = function loadThreeLegacy() {
        if (global.THREE && global.THREE.OrbitControls) {
            return Promise.resolve(global.THREE);
        }
        if (pending) {
            return pending;
        }
        var cfg = readConfig();
        var threeSrc = cfg.three || '/static/js/vendor/three.min.js';
        var controlsSrc = cfg.controls || '/static/js/vendor/OrbitControls.min.js';
        pending = loadScript(threeSrc)
            .then(function () {
                return loadScript(controlsSrc);
            })
            .then(function () {
                if (!global.THREE) {
                    throw new Error('THREE global missing after load');
                }
                return global.THREE;
            })
            .catch(function (err) {
                pending = null;
                throw err;
            });
        return pending;
    };
}(window));
