/**
 * lazy_markdown.js — Load marked + DOMPurify on demand for AI markdown rendering.
 */
(function (global) {
    'use strict';

    var pending = null;

    function readConfig() {
        var tag = document.getElementById('lazyMarkdownConfig');
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

    global.loadMarkdownLibs = function loadMarkdownLibs() {
        if (global.marked && global.DOMPurify) {
            return Promise.resolve();
        }
        if (pending) {
            return pending;
        }
        var cfg = readConfig();
        var markedSrc = cfg.marked || '/static/js/vendor/marked.min.js';
        var purifySrc = cfg.purify || 'https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js';
        pending = Promise.all([
            global.marked ? Promise.resolve() : loadScript(markedSrc),
            global.DOMPurify ? Promise.resolve() : loadScript(purifySrc),
        ]).catch(function (err) {
            pending = null;
            throw err;
        });
        return pending;
    };
}(window));
