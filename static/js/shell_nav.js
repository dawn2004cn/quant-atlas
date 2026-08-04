/**
 * shell_nav.js — Shell-preserving in-app navigation.
 *
 * Intercepts same-origin Flask page links, swaps #mainContent only,
 * keeps nav/footer/Jarvis chrome alive. Prefetches on hover.
 */
(function (global) {
    'use strict';

    var CACHE = new Map();
    var CACHE_MAX = 24;
    var loading = false;

    var PERSISTENT_SCRIPT_RE =
        /jquery|bootstrap|base_app\.js|api_client|state_bus|focus_context|persona_mask|scanner_events|compliance_footer|truth_badge|watchlist_quick|qa_user_center|api_error_banner|qa-focus-bar|qa-health-banner|qa-truth-badge|predictive_preload|shell_nav\.js|shell_deferred|lazy_echarts|lazy_markdown|lazy_mermaid|lazy_three_module|lazy_three_legacy|lazy_socketio|qa_markdown_safe|socket\.io/;

    function themeColors(theme) {
        if (theme === 'light') {
            return { bg: '#f6f8fb', text: '#0f172a' };
        }
        return { bg: '#07111f', text: '#eef6ff' };
    }

    function applyHtmlThemeColors(theme) {
        var c = themeColors(theme);
        var html = document.documentElement;
        html.style.backgroundColor = c.bg;
        html.style.color = c.text;
    }

    global.QAShellNav = global.QAShellNav || {};
    global.QAShellNav.applyHtmlThemeColors = applyHtmlThemeColors;
    global.QAShellNav.navigate = navigate;
    global.QAShellNav.prefetch = prefetch;

    function cacheSet(url, html) {
        if (CACHE.has(url)) {
            CACHE.delete(url);
        }
        CACHE.set(url, html);
        if (CACHE.size > CACHE_MAX) {
            var first = CACHE.keys().next().value;
            CACHE.delete(first);
        }
    }

    function isShellNavLink(a) {
        if (!a || a.tagName !== 'A') return false;
        if (a.getAttribute('data-shell-nav') === 'off') return false;
        if (a.target && a.target !== '_self') return false;
        if (a.hasAttribute('download')) return false;
        var href = a.getAttribute('href') || '';
        if (!href || href.charAt(0) === '#') return false;
        if (href.indexOf('javascript:') === 0) return false;
        try {
            var u = new URL(href, global.location.href);
            if (u.origin !== global.location.origin) return false;
            if (u.pathname.indexOf('/app/') === 0) return false;
            if (u.pathname === '/login' || u.pathname === '/register') return false;
            if (u.pathname.indexOf('/auth/') === 0) return false;
            return true;
        } catch (_err) {
            return false;
        }
    }

    function cloneScript(old) {
        var s = document.createElement('script');
        Array.prototype.slice.call(old.attributes).forEach(function (attr) {
            s.setAttribute(attr.name, attr.value);
        });
        if (old.src) {
            s.src = old.src;
            s.async = false;
        } else {
            s.textContent = old.textContent;
        }
        s.setAttribute('data-page-script', '1');
        return s;
    }

    function executeScripts(root) {
        var scripts = root.querySelectorAll('script');
        scripts.forEach(function (old) {
            var s = cloneScript(old);
            old.parentNode.replaceChild(s, old);
        });
    }

    function removePageScripts() {
        document.querySelectorAll('script[data-page-script]').forEach(function (s) {
            s.remove();
        });
    }

    function mergePageStyles(doc) {
        doc.querySelectorAll('link[rel="stylesheet"]').forEach(function (link) {
            var href = link.getAttribute('href');
            if (!href) return;
            if (href.indexOf('css/pages/') === -1 && href.indexOf('zen-finance.css') === -1) return;
            var abs = new URL(href, global.location.href).href;
            if (document.querySelector('link[rel="stylesheet"][href="' + abs + '"]')) return;
            var el = document.createElement('link');
            el.rel = 'stylesheet';
            el.href = abs;
            el.setAttribute('data-page-css', '1');
            document.head.appendChild(el);
        });
    }

    function warmPageStyles(doc) {
        doc.querySelectorAll('link[rel="stylesheet"]').forEach(function (link) {
            var href = link.getAttribute('href');
            if (!href || href.indexOf('css/pages/') === -1) return;
            var abs = new URL(href, global.location.href).href;
            if (document.querySelector('link[rel="stylesheet"][href="' + abs + '"]')) return;
            if (document.querySelector('link[rel="preload"][as="style"][href="' + abs + '"]')) return;
            var el = document.createElement('link');
            el.rel = 'preload';
            el.as = 'style';
            el.href = abs;
            document.head.appendChild(el);
        });
    }

    function syncBodyAttrs(doc) {
        if (!doc.body) return;
        var focusRefresh = doc.body.getAttribute('data-qa-focus-refresh');
        if (focusRefresh !== null) {
            document.body.setAttribute('data-qa-focus-refresh', focusRefresh);
        }
    }

    function syncNav(doc) {
        var ep = doc.body && doc.body.getAttribute('data-nav-endpoint');
        if (ep) document.body.setAttribute('data-nav-endpoint', ep);

        var newNav = doc.querySelector('.nav-links');
        var curNav = document.querySelector('.nav-links');
        if (!newNav || !curNav) return;

        curNav.querySelectorAll('a.active, .nav-pill.active').forEach(function (el) {
            el.classList.remove('active');
        });

        newNav.querySelectorAll('.nav-pill.active').forEach(function (a) {
            var id = a.id;
            if (!id) return;
            var cur = document.getElementById(id);
            if (cur) cur.classList.add('active');
        });

        newNav.querySelectorAll('a.active').forEach(function (a) {
            var href = a.getAttribute('href');
            if (!href || href === '#') return;
            curNav.querySelectorAll('a[href="' + href + '"]').forEach(function (el) {
                el.classList.add('active');
            });
        });
    }

    function runTailScripts(doc) {
        removePageScripts();
        doc.querySelectorAll('body script').forEach(function (old) {
            if (old.closest('#mainContent')) return;
            if (old.src && PERSISTENT_SCRIPT_RE.test(old.src)) return;
            document.body.appendChild(cloneScript(old));
        });
    }

    function reinitAfterSwap() {
        try {
            global.scrollTo(0, 0);
        } catch (_err) { /* ignore */ }

        var main = document.getElementById('mainContent');
        if (global.jQuery) {
            global.jQuery(document).trigger('qa:page-swapped');
            if (main) global.jQuery(main).trigger('qa:page-swapped');
        }
        if (global.QAFocusContext && typeof global.QAFocusContext.wireGlobalBar === 'function') {
            global.QAFocusContext.wireGlobalBar();
        }
    }

    function applyPage(doc, url, push) {
        var nextMain = doc.getElementById('mainContent');
        var curMain = document.getElementById('mainContent');
        if (!nextMain || !curMain) {
            global.location.href = url;
            return false;
        }

        mergePageStyles(doc);
        syncBodyAttrs(doc);
        curMain.innerHTML = nextMain.innerHTML;

        var title = doc.querySelector('title');
        if (title && title.textContent) {
            document.title = title.textContent;
        }

        syncNav(doc);
        executeScripts(curMain);
        runTailScripts(doc);

        if (push) {
            history.pushState({ shellNav: true, url: url }, '', url);
        }

        global.dispatchEvent(new CustomEvent('qa:page-swapped', { detail: { url: url } }));

        if (typeof global Alpine !== 'undefined' && global.Alpine.initTree) {
            try {
                global.Alpine.initTree(curMain);
            } catch (_err) { /* Alpine optional */ }
        }

        reinitAfterSwap();

        return true;
    }

    function fetchHtml(url) {
        if (CACHE.has(url)) {
            return Promise.resolve(CACHE.get(url));
        }
        return fetch(url, {
            credentials: 'include',
            headers: { Accept: 'text/html', 'X-Shell-Nav': '1' },
        }).then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            var ct = res.headers.get('content-type') || '';
            if (ct.indexOf('text/html') === -1) throw new Error('not html');
            return res.text();
        }).then(function (html) {
            cacheSet(url, html);
            try {
                var warmed = new DOMParser().parseFromString(html, 'text/html');
                warmPageStyles(warmed);
            } catch (_err) { /* ignore */ }
            return html;
        });
    }

    function navigate(url, push) {
        if (loading) return Promise.resolve();
        loading = true;
        var curMain = document.getElementById('mainContent');
        if (curMain) curMain.classList.add('page-wrap--nav-loading');

        return fetchHtml(url)
            .then(function (html) {
                var doc = new DOMParser().parseFromString(html, 'text/html');
                if (!applyPage(doc, url, push)) return;
            })
            .catch(function () {
                global.location.href = url;
            })
            .finally(function () {
                loading = false;
                if (curMain) curMain.classList.remove('page-wrap--nav-loading');
            });
    }

    function prefetch(url) {
        if (CACHE.has(url)) return;
        fetchHtml(url).catch(function () {});
    }

    document.addEventListener('click', function (e) {
        if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        var a = e.target.closest('a');
        if (!isShellNavLink(a)) return;
        var target = new URL(a.href, global.location.href);
        if (target.pathname === global.location.pathname && target.search === global.location.search) {
            return;
        }
        e.preventDefault();
        navigate(a.href, true);
    });

    global.addEventListener('popstate', function (e) {
        if (e.state && e.state.shellNav) {
            navigate(global.location.href, false);
        }
    });

    document.addEventListener('mouseover', function (e) {
        var a = e.target.closest('a');
        if (!isShellNavLink(a)) return;
        prefetch(a.href);
    }, { passive: true });

    if (global.history && global.history.replaceState) {
        global.history.replaceState({ shellNav: true, url: global.location.href }, '', global.location.href);
    }
})(window);
