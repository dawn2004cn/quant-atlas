/** 
 * Code splitting and lazy loading for Quant Atlas Jinja templates.
 * 
 * Defines critical (inline/head) vs deferred (after interaction) CSS/JS groups.
 * Reduces base template from 45 JS + 32 CSS to prioritized load groups.
 */

(function (global) {
    'use strict';

    var QC_ASSETS = global.QC_ASSETS || {};

    /**
     * Asset priority levels:
     * - critical: loaded synchronously in <head> (above-fold)
     * - interactive: loaded after first paint (below-fold, non-blocking)
     * - deferred: loaded on-demand (modals, charts, 3D)
     */
    var GROUPS = {
        critical: {
            css: [
                'css/design-tokens.css',
                'css/common.css',
                'css/fonts.css',
            ],
            js: [
                'js/vendor/jquery-3.7.1.min.js',
                'js/helpers/htmlescape.js',
                'js/api_client.js',
                'js/base_app.js',
            ],
        },
        interactive: {
            css: [
                'css/components/evidence-card.css',
                'css/components/trading-dna-spiral.css',
                'css/components/wisdom-mesh-browser.css',
            ],
            js: [
                'js/shell_nav.js',
                'js/state_bus.js',
                'js/focus_context.js',
                'js/persona_mask.js',
            ],
        },
        deferred: {
            css: [],
            js: [
                'js/vendor/echarts.min.js',
                'js/vendor/three.min.js',
                'js/vendor/mermaid.min.js',
                'js/vendor/lightweight-charts.standalone.production.js',
            ],
        },
    };

    /**
     * Load a group of assets with optional onload callback.
     */
    function loadGroup(groupName, callback) {
        var group = GROUPS[groupName];
        if (!group) return;
        var loaded = 0;
        var total = group.css.length + group.js.length;
        if (total === 0) { if (callback) callback(); return; }

        function onItem() {
            loaded++;
            if (loaded >= total && callback) callback();
        }

        group.css.forEach(function (href) {
            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = QC_ASSETS.versionedUrl ? QC_ASSETS.versionedUrl(href) : '/' + href;
            link.onload = onItem;
            link.onerror = onItem;
            document.head.appendChild(link);
        });

        group.js.forEach(function (src) {
            var script = document.createElement('script');
            script.src = QC_ASSETS.versionedUrl ? QC_ASSETS.versionedUrl(src) : '/' + src;
            script.async = true;
            script.onload = onItem;
            script.onerror = onItem;
            document.body.appendChild(script);
        });
    }

    function loadDeferred() { loadGroup('deferred'); }
    function loadInteractive(cb) { loadGroup('interactive', cb); }

    // Expose public API
    global.QCAssetLoader = {
        loadCritical: function () { loadGroup('critical'); },
        loadInteractive: loadInteractive,
        loadDeferred: loadDeferred,
        loadGroup: loadGroup,
        GROUPS: GROUPS,
    };

    // Auto-load interactive after DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            loadInteractive(function () { console.debug('[QCAsset] Interactive assets loaded'); });
        });
    } else {
        loadInteractive();
    }

})(window);
