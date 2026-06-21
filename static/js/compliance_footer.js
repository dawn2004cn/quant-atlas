(function (global) {
    'use strict';

    function applyManifest(manifest) {
        if (!manifest) return;
        var shortEl = document.getElementById('qcComplianceShort');
        var verEl = document.getElementById('qcComplianceVersion');
        var disclaimers = manifest.disclaimers || {};
        if (shortEl && disclaimers.short) {
            shortEl.textContent = disclaimers.short;
        }
        if (verEl && manifest.version) {
            verEl.textContent = '合规说明 v' + manifest.version + '（Beta SLA）';
        }
    }

    function load() {
        var path = '/api/v1/compliance/manifest';
        if (global.QCApi && typeof global.QCApi.get === 'function') {
            global.QCApi.get('/compliance/manifest').then(applyManifest).catch(function () { /* keep static fallback */ });
            return;
        }
        fetch(path)
            .then(function (r) { return r.json(); })
            .then(function (body) { applyManifest(body.data || body); })
            .catch(function () { /* keep static fallback */ });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})(window);
