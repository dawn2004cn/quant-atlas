/**
 * lazy_mermaid.js — Load Mermaid only when a diagram needs rendering.
 */
(function (global) {
    'use strict';

    var pending = null;

    function scriptSrc() {
        var tag = document.currentScript;
        if (tag && tag.getAttribute('data-mermaid-src')) {
            return tag.getAttribute('data-mermaid-src');
        }
        return '/static/js/vendor/mermaid.min.js';
    }

    global.loadMermaid = function loadMermaid(options) {
        if (global.mermaid) {
            if (options) {
                global.mermaid.initialize(Object.assign({ startOnLoad: false }, options));
            }
            return Promise.resolve(global.mermaid);
        }
        if (pending) {
            return pending;
        }
        pending = new Promise(function (resolve, reject) {
            var el = document.createElement('script');
            el.src = scriptSrc();
            el.onload = function () {
                if (global.mermaid) {
                    global.mermaid.initialize(Object.assign({ startOnLoad: false, theme: 'neutral' }, options || {}));
                    resolve(global.mermaid);
                } else {
                    pending = null;
                    reject(new Error('Mermaid failed to initialize'));
                }
            };
            el.onerror = function () {
                pending = null;
                reject(new Error('Mermaid failed to load'));
            };
            document.head.appendChild(el);
        });
        return pending;
    };
}(window));
