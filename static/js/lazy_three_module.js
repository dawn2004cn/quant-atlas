/**
 * lazy_three_module.js — Dynamic import THREE ES modules (CDN) on demand.
 */
(function (global) {
    'use strict';

    var cached = null;
    var pending = null;

    function readConfig() {
        var tag = document.getElementById('lazyThreeModuleConfig');
        if (!tag) {
            return {};
        }
        try {
            return JSON.parse(tag.textContent || '{}');
        } catch (_err) {
            return {};
        }
    }

    global.loadThreeModule = function loadThreeModule() {
        if (cached) {
            return Promise.resolve(cached);
        }
        if (pending) {
            return pending;
        }
        var cfg = readConfig();
        var threeUrl = cfg.three || 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
        var controlsUrl = cfg.controls || 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js';
        pending = Promise.all([
            import(threeUrl),
            import(controlsUrl),
        ])
            .then(function (parts) {
                cached = {
                    THREE: parts[0],
                    OrbitControls: parts[1].OrbitControls,
                };
                global.__ThreeModule = cached;
                global.__DecisionReplayThree = cached;
                global.dispatchEvent(new Event('decision-replay-three-ready'));
                return cached;
            })
            .catch(function (err) {
                pending = null;
                throw err;
            });
        return pending;
    };
}(window));
