(function (global) {
    'use strict';

    function esc(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    async function load(symbol, market, options) {
        var opts = options || {};
        var role = opts.role || '';
        var url = '/api/v1/stocks/' + encodeURIComponent(market || 'CN') + '/' +
            encodeURIComponent(symbol) + '/decision-brief';
        if (role) url += '?role=' + encodeURIComponent(role);
        var res = await fetch(url, { credentials: 'include' });
        var json = await res.json();
        if (!res.ok) throw new Error(((json.error || {}).message) || 'decision brief failed');
        return json.data || {};
    }

    function render(container, brief) {
        var el = typeof container === 'string' ? document.querySelector(container) : container;
        if (!el) return;
        var components = brief.components || [];
        el.innerHTML = components.map(renderComponent).join('');
    }

    function renderComponent(component) {
        if (component.type === 'quote_strip') return renderQuote(component);
        if (component.type === 'risk_banner') return renderRisk(component);
        if (component.type === 'evidence_timeline') return renderTimeline(component);
        if (component.type === 'action_bar') return renderActions(component);
        return '';
    }

    function renderQuote(component) {
        var p = component.payload || {};
        return '<section class="qa-brief qa-brief-quote">' +
            '<div class="qa-brief-title">' + esc(component.title) + '</div>' +
            '<div class="qa-brief-main">' + esc(p.price == null ? '--' : p.price) + '</div>' +
            '<div class="qa-brief-muted">' + esc((p.fact || {}).close_fact || '') + '</div>' +
            '</section>';
    }

    function renderRisk(component) {
        var p = component.payload || {};
        return '<section class="qa-brief qa-brief-risk qa-brief-' + esc(component.severity || 'info') + '">' +
            '<div class="qa-brief-title">' + esc(component.title) + '</div>' +
            '<div>' + esc(p.coverage_level || 'unknown') + ' · ' + esc(p.coverage_pct == null ? '--' : p.coverage_pct + '%') + '</div>' +
            '<div class="qa-brief-muted">' + esc(p.warning || '') + '</div>' +
            '</section>';
    }

    function renderTimeline(component) {
        var p = component.payload || {};
        var markers = p.markers || [];
        return '<section class="qa-brief qa-brief-timeline">' +
            '<div class="qa-brief-title">' + esc(component.title) + '</div>' +
            markers.map(function (m) {
                return '<div class="qa-brief-marker"><span>' + esc(m.date || '') + '</span><b>' +
                    esc(m.type || '') + '</b><span>' + esc(m.title || '') + '</span></div>';
            }).join('') +
            '</section>';
    }

    function renderActions(component) {
        var items = ((component.payload || {}).items || []);
        return '<section class="qa-brief qa-brief-actions">' +
            items.map(function (a) {
                return '<a class="btn-soft btn-sm" href="' + esc(a.href || '#') + '">' + esc(a.label || a.id) + '</a>';
            }).join('') +
            '</section>';
    }

    global.QADecisionBrief = {
        load: load,
        render: render,
        renderComponent: renderComponent
    };
})(window);
