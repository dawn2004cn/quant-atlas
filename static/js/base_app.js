/**
 * base_app.js — Shared utilities extracted from base.html template.
 *
 * Responsibilities:
 *   - Jarvis command orb (open/close, intent parsing, quick prompts)
 *   - Theme toggle + persistence
 *   - Toast notification system
 *   - Confirm dialog
 *   - Message badge polling
 *   - Mobile nav toggle
 *   - CSRF token injection for authenticated API calls
 */

/* ── Theme ─────────────────────────────────────────────────────────── */

function toggleTheme() {
    var html = document.documentElement;
    var isDark = html.getAttribute('data-theme') === 'dark';
    var newTheme = isDark ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    html.style.colorScheme = newTheme;
    localStorage.setItem('theme', newTheme);
    if (window.QAShellNav && window.QAShellNav.applyHtmlThemeColors) {
        window.QAShellNav.applyHtmlThemeColors(newTheme);
    }
}

/* Theme icons follow [data-theme] via common.css — no per-icon display toggling. */

/* ── Toast system ──────────────────────────────────────────────────── */

/**
 * Unified error logger: shows a toast to the user AND logs to console.
 * Usage: replace `console.error(msg)` with `qcLogError(msg, err)`.
 */
window.qcLogError = function (msg, err) {
    var detail = err ? (err.message || String(err)) : '';
    var display = detail ? (msg + ': ' + detail) : msg;
    if (typeof window.showToast === 'function') {
        window.showToast(display, 'error', 5000);
    }
    console.error(msg, err || '');
};

window._toasts = [];

window.showToast = function (message, type, duration) {
    type = type || 'info';
    duration = duration || 3000;
    var id = 'toast-' + Date.now();
    var container = document.getElementById('toastContainer') || (function () {
        var d = document.createElement('div');
        d.id = 'toastContainer';
        d.className = 'toast-container';
        document.body.appendChild(d);
        return d;
    })();
    var icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    var icon = icons[type] || icons.info;
    var t = document.createElement('div');
    t.id = id;
    t.className = 'toast-item toast-' + type;
    t.innerHTML = '<span class="toast-icon">' + icon + '</span><span class="toast-message">' + message + '</span><button type="button" class="toast-close" data-toast-dismiss="' + id + '">&times;</button>';
    container.appendChild(t);
    var closeBtn = t.querySelector('[data-toast-dismiss]');
    if (closeBtn) {
        closeBtn.addEventListener('click', function () { dismissToast(id); });
    }
    window._toasts.push({ id: id, el: t });
    setTimeout(function () { dismissToast(id); }, duration);
    return id;
};

window.dismissToast = function (id) {
    for (var i = 0; i < window._toasts.length; i++) {
        if (window._toasts[i].id === id) {
            var el = window._toasts[i].el;
            el.classList.add('toast-hide');
            (function (e) { setTimeout(function () { e.remove(); }, 300); })(el);
            window._toasts.splice(i, 1);
            break;
        }
    }
};

/* ── Confirm dialog ────────────────────────────────────────────────── */

window.confirmAction = function (message, onConfirm) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'confirmOverlay';
    overlay.innerHTML = '<div class="modal-confirm"><div class="modal-confirm-body">' + message + '</div><div class="modal-confirm-actions"><button type="button" class="btn-soft" id="confirmCancel">取消</button><button type="button" class="btn-brand" id="confirmYes">确定</button></div></div>';
    document.body.appendChild(overlay);
    var yesBtn = document.getElementById('confirmYes');
    var cancelBtn = document.getElementById('confirmCancel');
    if (cancelBtn) cancelBtn.addEventListener('click', closeConfirm);
    if (yesBtn) yesBtn.addEventListener('click', function () { closeConfirm(); if (onConfirm) onConfirm(); });
    overlay.onclick = function (e) { if (e.target === overlay) closeConfirm(); };
};

window.closeConfirm = function () {
    var el = document.getElementById('confirmOverlay');
    if (el) el.remove();
};

/* ── Jarvis command orb ────────────────────────────────────────────── */

window.openCommandOrb = function () {
    var orb = document.getElementById('commandOrb');
    var input = document.getElementById('jarvisInput');
    if (!orb) return;
    orb.classList.add('is-open');
    setTimeout(function () { if (input) input.focus(); }, 30);
};

window.setJarvis = function (txt) {
    var inp = document.getElementById('jarvisInput');
    if (!inp) return;
    inp.value = txt;
    inp.dispatchEvent(new Event('input'));
};

(function () {
    var orb = document.getElementById('commandOrb');
    var input = document.getElementById('jarvisInput');
    var feedback = document.getElementById('jarvisFeedback');
    if (!orb || !input || !feedback) return;

    var debounceTimer;

    // Keyboard shortcuts
    window.addEventListener('keydown', function (e) {
        if (e.key === '/' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            window.openCommandOrb();
        }
        if (e.key === 'Escape') orb.classList.remove('is-open');
    });

    // Click outside to close
    orb.onclick = function (e) { if (e.target === orb) orb.classList.remove('is-open'); };

    // Intent parsing
    input.oninput = function () {
        clearTimeout(debounceTimer);
        var q = input.value.trim();
        if (!q) {
            feedback.innerHTML = '<div class="muted">输入指令...</div>';
            return;
        }

        // Strategy generation keywords
        var strategyKeywords = ['策略', '写策略', '生成策略', '策略代码', '编写策略', '交易策略', 'strategy', '写代码', '生成代码'];
        var isStrategyRequest = strategyKeywords.some(function (kw) {
            return q.toLowerCase().indexOf(kw.toLowerCase()) !== -1;
        });

        if (isStrategyRequest) {
            feedback.innerHTML = '<div style="display:flex; justify-content:space-between; align-items:center; animation:fadeIn 0.2s;"><div style="font-weight:800; color:var(--positive);">🤠 进入 AI 策略生成器</div><span class="badge-soft">按下回车跳转</span></div>';
            input.onkeydown = function (e) {
                if (e.key === 'Enter') {
                    location.href = '/nl-strategy?prompt=' + encodeURIComponent(q);
                }
            };
            return;
        }

        debounceTimer = setTimeout(function () {
            feedback.innerHTML = '<div class="loading-state" style="padding:10px; border:none;">🤖 贾维斯正在解析意图...</div>';
            fetch('/api/v1/system/ask?q=' + encodeURIComponent(q))
                .then(function (res) { return res.json(); })
                .then(function (json) {
                    var d = json.data || json;
                    var extra = '';
                    if (d.intent === 'pattern_stock_pick' && d.candidates && d.candidates.length) {
                        var names = d.candidates.slice(0, 3).map(function (c) { return c.name || c.symbol; }).join('、');
                        extra = '<div class="text-xs text-muted mt-1">候选：' + names + '</div>';
                    }
                    feedback.innerHTML = '<div style="animation:fadeIn 0.2s;"><div style="display:flex; justify-content:space-between; align-items:center;"><div style="font-weight:800; color:var(--brand);">' + (d.label || '已识别意图') + '</div><span class="badge-soft">按下回车确认</span></div>' + extra + '</div>';
                    input.onkeydown = function (e) { if (e.key === 'Enter' && d.url) location.href = d.url; };
                })
                .catch(function () {
                    feedback.innerHTML = '<div class="negative">意图识别暂时掉线</div>';
                });
        }, 400);
    };
})();

function bindBaseChromeActions() {
    var openBtn = document.getElementById('commandOpenBtn');
    if (openBtn) openBtn.addEventListener('click', window.openCommandOrb);
    var mobileJarvis = document.getElementById('mobileJarvisBtn');
    if (mobileJarvis) mobileJarvis.addEventListener('click', window.openCommandOrb);
    var themeBtn = document.getElementById('themeToggle');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
    document.querySelectorAll('[data-jarvis-prompt]').forEach(function (el) {
        el.addEventListener('click', function () {
            window.setJarvis(el.getAttribute('data-jarvis-prompt') || '');
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindBaseChromeActions);
} else {
    bindBaseChromeActions();
}

/* ── Nav polling ──────────────────────────────────────────────────── */

var qcPollingExpired = false;

function stopQcPolling() {
    qcPollingExpired = true;
}

window.__QC_MC_SEEN = 'quantMsgLastSeenTs';

window.updateNavMessageBadge = function () {
    var seen = localStorage.getItem(window.__QC_MC_SEEN) || '';
    var url = '/api/v1/system/task-messages?limit=80';
    if (seen) url += '&since_ts=' + encodeURIComponent(seen);
    var psychUrl = '/api/v1/system/task-messages?limit=40&category=retail_psychology';
    if (seen) psychUrl += '&since_ts=' + encodeURIComponent(seen);

    $.when($.getJSON(url), $.getJSON(psychUrl)).done(function (allRes, psychRes) {
        var d = (allRes[0].data !== undefined ? allRes[0].data : allRes[0]) || {};
        var psychD = (psychRes[0].data !== undefined ? psychRes[0].data : psychRes[0]) || {};
        var items = d.items || [];
        var psychItems = psychD.items || [];
        var $badges = $('.js-nav-bell-badge');
        var $link = $('#navMsgLink');
        if (!seen) {
            $badges.removeClass('show').text('');
            if ($link.length) $link.attr('title', '消息中心');
            return;
        }
        var n = items.length;
        var pn = psychItems.length;
        if (n > 0) {
            var label = n > 99 ? '99+' : String(n);
            if (pn > 0 && pn <= n) label = pn + '/' + label;
            $badges.text(label).addClass('show');
            if (pn > 0) { $badges.addClass('psych'); } else { $badges.removeClass('psych'); }
            if ($link.length) {
                $link.attr('title', pn > 0 ? ('消息中心（听 ' + pn + '条心理提醒）') : '消息中心');
                if (pn > 0) {
                    $link.attr('href', $link.attr('href').split('?')[0] + '?filter=psychology');
                }
            }
        } else {
            $badges.removeClass('show psych').text('');
            if ($link.length) {
                $link.attr('title', '消息中心');
            }
        }
    }).fail(function (xhr) {
        if (xhr && xhr.status === 401) { stopQcPolling(); }
        $('.js-nav-bell-badge').removeClass('show').text('');
    });
};

window.updateNavAlertBadge = function () {
    $.getJSON('/api/v1/system/alerts/summary').done(function (res) {
        var d = res.data !== undefined ? res.data : res;
        var critical = Number(d.critical_count || 0);
        var warning = Number(d.warning_count || 0);
        var n = critical > 0 ? critical : warning;
        var $badges = $('.js-nav-alert-badge');
        if (n > 0) {
            $badges.text(n > 99 ? '99+' : String(n)).show();
        } else {
            $badges.hide().text('');
        }
    }).fail(function (xhr) {
        if (xhr && xhr.status === 401) { stopQcPolling(); }
        $('.js-nav-alert-badge').hide().text('');
    });
};

/* ── Mobile nav toggle ────────────────────────────────────────────── */

/* ── Nav group collapsible (native capture — survives Bootstrap stopPropagation) ── */

(function () {
    function toggleNavGroupHeader(header) {
        var isExpanded = header.getAttribute('aria-expanded') === 'true';
        var nextExpanded = !isExpanded;
        header.setAttribute('aria-expanded', String(nextExpanded));
        var body = header.nextElementSibling;
        if (!body || !body.classList.contains('nav-group-body')) {
            return;
        }
        body.classList.toggle('is-collapsed', !nextExpanded);
        body.classList.toggle('is-open', nextExpanded);
    }

    document.addEventListener('click', function (e) {
        var header = e.target.closest('.nav-group-header');
        if (!header || !header.closest('.dropdown-menu')) {
            return;
        }
        e.preventDefault();
        e.stopPropagation();
        toggleNavGroupHeader(header);
    }, true);

    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Enter' && e.key !== ' ') {
            return;
        }
        var header = e.target.closest('.nav-group-header');
        if (!header || !header.closest('.dropdown-menu')) {
            return;
        }
        e.preventDefault();
        e.stopPropagation();
        toggleNavGroupHeader(header);
    }, true);
})();

$(function () {
    // Message badge polling
    if ($('.js-nav-bell-badge').length) {
        window.updateNavMessageBadge();
        setInterval(function () {
            if (!qcPollingExpired) window.updateNavMessageBadge();
        }, 45000);
    }
    // Alert badge polling
    if ($('.js-nav-alert-badge').length) {
        window.updateNavAlertBadge();
        setInterval(function () {
            if (!qcPollingExpired) window.updateNavAlertBadge();
        }, 45000);
    }
    // Mobile nav toggle
    var $nav = $('.app-nav');
    var $btn = $('#navToggleBtn');
    if ($btn.length) {
        var setExpanded = function (open) {
            $nav.toggleClass('qc-nav-open', !!open);
            $btn.attr('aria-expanded', open ? 'true' : 'false');
        };
        $btn.on('click', function () { setExpanded(!$nav.hasClass('qc-nav-open')); });
        $(document).on('click', function (e) {
            if (window.matchMedia && window.matchMedia('(max-width: 640px)').matches) {
                if (!$nav.is(e.target) && $nav.has(e.target).length === 0) setExpanded(false);
            }
        });
        $nav.on('click', 'a', function () {
            if (window.matchMedia && window.matchMedia('(max-width: 640px)').matches) setExpanded(false);
        });
    }

    /* ── Nav search ───────────────────────────────────────────────── */
    $('[data-nav-search]').on('input', function () {
        var wrapper = $(this).closest('.nav-search-wrapper');
        var query = $(this).val().trim().toLowerCase();
        var filtering = query.length > 0;
        wrapper.toggleClass('nav-search-filtering', filtering);
        var items = wrapper.find('[data-nav-label]');
        var anyVisible = false;
        var groups = wrapper.find('.nav-group');

        // Auto-open nav-groups when searching
        if (query && groups.length) {
            groups.each(function () {
                var $body = $(this).find('.nav-group-body');
                var visibleInGroup = $body.find('[data-nav-label]').filter(function () {
                    var label = $(this).attr('data-nav-label') || '';
                    return !query || label.indexOf(query) !== -1;
                });
                if (visibleInGroup.length && $body.hasClass('is-collapsed')) {
                    $(this).find('.nav-group-header').attr('aria-expanded', 'true');
                    $body.removeClass('is-collapsed').addClass('is-open');
                }
            });
        }

        items.each(function () {
            var label = $(this).attr('data-nav-label') || '';
            if (!query || label.indexOf(query) !== -1) {
                $(this).show().addClass('nav-search-match');
                anyVisible = true;
                // Also show the parent nav-group-body so the item is visible
                var $body = $(this).closest('.nav-group-body');
                if ($body.length && $body.hasClass('is-collapsed')) {
                    $body.removeClass('is-collapsed').addClass('is-open');
                    $body.closest('.nav-group').find('.nav-group-header').attr('aria-expanded', 'true');
                }
            } else {
                $(this).removeClass('nav-search-match');
                if (filtering && $(this).css('display') !== 'none') {
                    $(this).hide();
                }
            }
        });

        if (!filtering) {
            items.removeClass('nav-search-match').css('display', '');
        }

        // Show "no results" when nothing matches
        var $noResults = wrapper.find('.nav-search-no-results');
        if (query && !anyVisible) {
            $noResults.show();
        } else {
            $noResults.hide();
        }
    });

    // Clear search on dropdown close
    $('.dropdown-menu').on('hidden.bs.dropdown', function () {
        var $wrapper = $(this).filter('.nav-search-wrapper').add($(this).find('.nav-search-wrapper'));
        $wrapper.removeClass('nav-search-filtering');
        $(this).find('[data-nav-search]').val('').trigger('input');
    });

    // Auto-open the group whose item is active (others stay default-expanded)
    $('.nav-group').each(function () {
        var $body = $(this).find('.nav-group-body');
        var $active = $body.find('.dropdown-item.active');
        if ($active.length) {
            $(this).find('.nav-group-header').attr('aria-expanded', 'true');
            $body.removeClass('is-collapsed').addClass('is-open');
        }
    });
});

/* ── Quant Realtime (Socket.IO) ───────────────────────────────────── */

(function () {
    if (typeof io === 'undefined') return;

    function initQuantRealtime() {
        var socket = io({
            path: '/socket.io',
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 2,
            reconnectionDelay: 8000,
            timeout: 8000,
        });

        socket.on('connect', function () {
            console.debug('[QuantRealtime] connected');
            socket.emit('subscribe', { room: 'market' });
            socket.emit('subscribe', { room: 'alerts' });
            window.QuantRealtime.connected = true;
        });

        socket.on('disconnect', function () {
            window.QuantRealtime.connected = false;
        });

        socket.on('quote_update', function (d) {
            window.QuantRealtime.lastQuote = d;
            window.QuantRealtime.lastQuoteAt = Date.now();
            document.dispatchEvent(new CustomEvent('quant:quote', { detail: d }));
        });

        socket.on('CrossTeamSiteAlertEvent', function (d) {
            document.dispatchEvent(new CustomEvent('quant:cross-team-alert', { detail: d }));
        });

        window.QuantRealtime.socket = socket;
    }

    window.QuantRealtime = window.QuantRealtime || {};

    fetch('/api/v1/health', {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
    })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (payload) {
            if (payload && payload.realtime && payload.realtime.socketio_available) {
                initQuantRealtime();
            }
        })
        .catch(function () {
            /* SocketIO optional in dev */
        });
})();

/* ── CSRF token injection for authenticated API calls ───────────────── */

(function () {
    // Cached CSRF token from server-rendered template helper
    var cachedToken = null;

    /**
     * Get the current CSRF token.
     * Tries: cached → meta tag → Jinja global injected into window → fallback null.
     */
    window.getCsrfToken = function () {
        if (cachedToken) return cachedToken;
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) { cachedToken = meta.getAttribute('content'); return cachedToken; }
        if (window.__CSRF_TOKEN__) { cachedToken = window.__CSRF_TOKEN__; return cachedToken; }
        return null;
    };

    /**
     * Set CSRF token from Jinja global (called by base.html template).
     * Kept for backwards-compatibility with templates that still inject directly.
     */
    window.__setCsrfToken__ = function (token) {
        cachedToken = token;
    };

    function apiPathNeedsCsrf(url) {
        if (!url) return false;
        var s = String(url);
        return s.indexOf('/api/') >= 0;
    }

    function withCsrfHeaders(headers) {
        var token = window.getCsrfToken();
        if (!token) return headers || {};
        headers = headers || {};
        if (!headers['X-CSRF-Token'] && !headers['X-CSRFToken']) {
            headers['X-CSRFToken'] = token;
            headers['X-CSRF-Token'] = token;
        }
        return headers;
    }

    /**
     * Enhanced fetch that auto-injects X-CSRF-Token header for POST/PUT/DELETE/PATCH
     * requests to /api/* paths when a session CSRF token is available.
     */
    var origFetch = window.fetch;
    window.fetch = function (url, options) {
        options = options || {};
        var method = (options.method || 'GET').toUpperCase();
        if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') {
            return origFetch.apply(this, arguments);
        }
        var urlString = typeof url === 'string' ? url : (url && url.toString ? String(url) : '');
        if (!apiPathNeedsCsrf(urlString)) {
            return origFetch.apply(this, arguments);
        }
        options.headers = withCsrfHeaders(options.headers);
        return origFetch.call(this, url, options);
    };

    /** jQuery $.ajax / $.post — same CSRF contract as fetch. */
    if (window.jQuery && window.jQuery.ajaxPrefilter) {
        window.jQuery.ajaxPrefilter(function (options) {
            var method = (options.type || options.method || 'GET').toUpperCase();
            if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') {
                return;
            }
            if (!apiPathNeedsCsrf(options.url)) {
                return;
            }
            options.headers = withCsrfHeaders(options.headers);
        });
    }
})();
