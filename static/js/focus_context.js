(function (global) {
    'use strict';

    var STORAGE_KEY = 'qa_focus_context';
    var MARKETS = ['CN', 'HK', 'US', 'CRYPTO'];

    var SHARE_TEMPLATES = [
        { page: 'stock_detail', label: '个股', path: '/stock/{symbol}?m={market}' },
        { page: 'ai_analysis', label: 'AI', path: '/ai-analysis?symbol={symbol}&market={market}' },
        { page: 'workbench', label: '操盘台', path: '/?symbol={symbol}&market={market}' },
        { page: 'backtest', label: '回测', path: '/backtest?symbol={symbol}&market={market}' }
    ];

    function normalizeSymbol(symbol) {
        var raw = String(symbol || '').trim();
        if (!raw) return '';
        if (raw.indexOf(':') >= 0) {
            raw = raw.split(':').pop();
        }
        if (/^(SH|SZ|BJ)\d{6}$/i.test(raw)) {
            return raw.slice(2).toUpperCase();
        }
        return raw.toUpperCase();
    }

    function normalizeMarket(market) {
        var m = String(market || 'CN').trim().toUpperCase();
        return MARKETS.indexOf(m) >= 0 ? m : 'CN';
    }

    function readUrlFocus() {
        try {
            var params = new URLSearchParams(global.location.search || '');
            var pathSym = readPathSymbol();
            return {
                symbol: normalizeSymbol(params.get('symbol') || pathSym || ''),
                market: normalizeMarket(params.get('market') || params.get('m') || 'CN'),
            };
        } catch (e) {
            return { symbol: '', market: 'CN' };
        }
    }

    function readPathSymbol() {
        var m = (global.location.pathname || '').match(/^\/stock\/([^/?#]+)/i);
        return m ? decodeURIComponent(m[1]) : '';
    }

    function readStoredFocus() {
        try {
            var raw = global.localStorage.getItem(STORAGE_KEY);
            if (!raw) return { symbol: '', market: 'CN' };
            var data = JSON.parse(raw);
            return {
                symbol: normalizeSymbol(data.symbol),
                market: normalizeMarket(data.market),
            };
        } catch (e) {
            return { symbol: '', market: 'CN' };
        }
    }

    function saveStoredFocus(focus) {
        try {
            global.localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({
                    symbol: normalizeSymbol(focus.symbol),
                    market: normalizeMarket(focus.market),
                })
            );
        } catch (e) {
            /* ignore quota errors */
        }
    }

    function syncUrl(focus, replace) {
        if (focus.skipUrl) return;
        try {
            var url = new URL(global.location.href);
            if (focus.symbol) {
                url.searchParams.set('symbol', focus.symbol);
            } else {
                url.searchParams.delete('symbol');
            }
            url.searchParams.set('market', normalizeMarket(focus.market));
            var method = replace ? 'replaceState' : 'pushState';
            global.history[method]({}, '', url.toString());
        } catch (e) {
            /* ignore */
        }
    }

    function dispatchChange(focus) {
        try {
            global.document.dispatchEvent(new CustomEvent('qa:focus-change', { detail: focus }));
        } catch (e) {
            /* ignore */
        }
    }

    function getFocus() {
        var fromUrl = readUrlFocus();
        if (fromUrl.symbol) {
            saveStoredFocus(fromUrl);
            return fromUrl;
        }
        return readStoredFocus();
    }

    function setFocus(symbol, market, options) {
        var opts = options || {};
        var focus = {
            symbol: normalizeSymbol(symbol),
            market: normalizeMarket(market || readStoredFocus().market || 'CN'),
            skipUrl: !!opts.skipUrl,
        };
        saveStoredFocus(focus);
        if (!opts.skipUrl) {
            syncUrl(focus, !!opts.replace);
        }
        if (!opts.silent) {
            dispatchChange(focus);
        }
        refreshGlobalBar(focus);
        if (typeof opts.onChange === 'function') {
            opts.onChange(focus);
        }
        return focus;
    }

    function appendQuery(url, focus) {
        if (!url || !focus || !focus.symbol) return url;
        var sep = url.indexOf('?') >= 0 ? '&' : '?';
        return url + sep + 'symbol=' + encodeURIComponent(focus.symbol) + '&market=' + encodeURIComponent(focus.market);
    }

    function buildShareLinks(focus) {
        if (!focus || !focus.symbol) return [];
        return SHARE_TEMPLATES.map(function (t) {
            return {
                page: t.page,
                label: t.label,
                href: t.path
                    .replace('{symbol}', encodeURIComponent(focus.symbol))
                    .replace('{market}', encodeURIComponent(focus.market)),
            };
        });
    }

    function renderShareLinks(container, focus) {
        if (!container) return;
        var links = buildShareLinks(focus);
        if (!links.length) {
            container.innerHTML = '<span class="qc-global-focus-hint">设置焦点后可一键跳转各功能区</span>';
            return;
        }
        container.innerHTML = links.map(function (l) {
            return '<a class="qc-global-focus-link" href="' + l.href + '">' + l.label + '</a>';
        }).join('');
    }

    function refreshGlobalBar(focus) {
        var symEl = global.document.getElementById('qcGlobalFocusSymbol');
        var mktEl = global.document.getElementById('qcGlobalFocusMarket');
        var linksEl = global.document.getElementById('qcGlobalFocusLinks');
        if (!symEl || !mktEl) return;
        var f = focus || getFocus();
        symEl.value = f.symbol || '';
        mktEl.value = normalizeMarket(f.market);
        renderShareLinks(linksEl, f);
    }

    function wireGlobalBar() {
        var bar = global.document.getElementById('qcGlobalFocusBar');
        if (!bar || bar.getAttribute('data-wired') === '1') return;
        bar.setAttribute('data-wired', '1');
        refreshGlobalBar(getFocus());

        var applyBtn = global.document.getElementById('qcGlobalFocusApply');
        var clearBtn = global.document.getElementById('qcGlobalFocusClear');
        var symEl = global.document.getElementById('qcGlobalFocusSymbol');

        if (applyBtn) {
            applyBtn.addEventListener('click', function () {
                setFocus(symEl.value, global.document.getElementById('qcGlobalFocusMarket').value, { replace: true });
            });
        }
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                setFocus('', 'CN', { replace: true });
            });
        }
        if (symEl) {
            symEl.addEventListener('keydown', function (ev) {
                if (ev.key === 'Enter') {
                    ev.preventDefault();
                    setFocus(symEl.value, global.document.getElementById('qcGlobalFocusMarket').value, { replace: true });
                }
            });
        }
    }

    function decorateFocusLinks(root) {
        var scope = root || global.document;
        var focus = getFocus();
        if (!focus.symbol) return;
        scope.querySelectorAll('a[data-qa-focus-link]').forEach(function (a) {
            var base = a.getAttribute('href') || a.getAttribute('data-base-href') || '';
            if (!a.getAttribute('data-base-href')) {
                a.setAttribute('data-base-href', base);
            }
            a.setAttribute('href', appendQuery(base, focus));
        });
    }

    function init() {
        wireGlobalBar();
        decorateFocusLinks();
        global.document.addEventListener('qa:focus-change', function () {
            decorateFocusLinks();
        });
    }

    if (global.document.readyState === 'loading') {
        global.document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    global.QAFocusContext = {
        getFocus: getFocus,
        setFocus: setFocus,
        appendQuery: appendQuery,
        buildShareLinks: buildShareLinks,
        normalizeSymbol: normalizeSymbol,
        normalizeMarket: normalizeMarket,
        wireGlobalBar: wireGlobalBar,
        refreshGlobalBar: refreshGlobalBar,
    };
})(window);
