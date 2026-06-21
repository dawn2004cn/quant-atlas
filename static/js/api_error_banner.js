(function (global) {
    'use strict';

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function extractError(payload) {
        if (!payload || typeof payload !== 'object') {
            return { code: 'unknown', message: String(payload || '未知错误'), hints: [] };
        }
        var err = payload.error || payload;
        return {
            code: err.code || payload.code || 'unknown',
            message: err.message || payload.message || '请求失败',
            hints: err.hints || payload.hints || [],
        };
    }

    function hintActionHtml(hint) {
        if (!hint) return '';
        var kind = hint.action_kind || 'link';
        var label = esc(hint.action_label || '查看');
        if (kind === 'refresh') {
            return '<button type="button" class="btn-soft btn-sm qc-api-error-action" data-action="refresh">' + label + '</button>';
        }
        var href = esc(hint.action_href || '#');
        return '<a class="btn-soft btn-sm qc-api-error-action" href="' + href + '">' + label + '</a>';
    }

    function renderBanner(el, payload, options) {
        var opts = options || {};
        var target = typeof el === 'string' ? document.querySelector(el) : el;
        if (!target) return;
        var err = extractError(payload);
        var hint = (err.hints && err.hints[0]) || null;
        var title = hint && hint.title ? hint.title : '操作未能完成';
        var body = hint && hint.body ? hint.body : err.message;
        var html =
            '<div class="qc-ux-banner__title">' + esc(title) + '</div>' +
            '<div class="qc-ux-banner__body">' + esc(body) + '</div>' +
            '<div class="qc-api-error-actions">' +
            hintActionHtml(hint) +
            (opts.retryCallback ? '<button type="button" class="btn-brand btn-sm qc-api-error-retry">重试</button>' : '') +
            '</div>';
        target.className = 'qc-ux-banner qc-ux-banner--danger';
        target.innerHTML = html;
        target.style.display = '';
        var refreshBtn = target.querySelector('[data-action="refresh"]');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function () {
                global.location.reload();
            });
        }
        var retryBtn = target.querySelector('.qc-api-error-retry');
        if (retryBtn && typeof opts.retryCallback === 'function') {
            retryBtn.addEventListener('click', opts.retryCallback);
        }
    }

    function messageFromResponse(payload) {
        return extractError(payload).message;
    }

    global.QCApiError = {
        extractError: extractError,
        renderBanner: renderBanner,
        messageFromResponse: messageFromResponse,
    };
})(window);
