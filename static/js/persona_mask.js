/**
 * persona_mask.js — UI feature masking based on User Persona tier
 *
 * On page load, fetches GET /api/v1/user/persona and evaluates feature_mask.
 * Any element with data-feature="<feature_key>" will be shown/hidden
 * according to the boolean value in the mask.
 *
 * Usage in templates:
 *   <div data-feature="show_qlib_backtest"> ... </div>
 */
(function (global) {
    'use strict';

    var MASK_ATTR = 'data-feature';

    function applyMask(mask) {
        if (!mask || typeof mask !== 'object') return;
        var els = document.querySelectorAll('[' + MASK_ATTR + ']');
        var count = 0;
        els.forEach(function (el) {
            var key = el.getAttribute(MASK_ATTR);
            if (key && mask.hasOwnProperty(key)) {
                if (mask[key]) {
                    el.style.removeProperty('display');
                } else {
                    el.style.display = 'none';
                }
                count++;
            }
        });
        if (count > 0) {
            // Dispatch event so other components know masking completed
            document.dispatchEvent(new CustomEvent('qa:persona-mask-applied', {
                detail: { elements: count, mask: mask }
            }));
        }
    }

    async function loadAndApply() {
        try {
            var res = await fetch('/api/v1/user/persona');
            if (!res.ok) return;
            var body = await res.json();
            var data = body.data || body;
            var mask = data.features || data.feature_mask;
            if (mask) {
                applyMask(mask);
                // Cache in QCStateBus for reactive components
                if (global.QCStateBus) {
                    global.QCStateBus.publish('user.persona', data, { persist: false });
                }
            }
        } catch (_) {
            // silently skip — masks only enhance, shouldn't break page
        }
    }

    // Auto-run after DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadAndApply);
    } else {
        loadAndApply();
    }

    // Export for imperative use
    global.QAPersonaMask = { loadAndApply: loadAndApply, applyMask: applyMask };
})(window);
