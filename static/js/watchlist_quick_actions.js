(function () {
    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function normalizeSymbol(symbol) {
        var raw = String(symbol || '').trim();
        if (!raw) return '';
        if (raw.indexOf(':') >= 0) {
            raw = raw.split(':').pop();
        }
        return raw.toUpperCase();
    }

    function ensureToast() {
        var el = document.getElementById('qcWatchlistToast');
        if (el) return el;
        el = document.createElement('div');
        el.id = 'qcWatchlistToast';
        el.style.cssText = [
            'position:fixed',
            'right:22px',
            'bottom:22px',
            'z-index:2000',
            'max-width:360px',
            'padding:14px 16px',
            'border-radius:18px',
            'box-shadow:0 18px 42px rgba(16,33,52,.18)',
            'background:var(--surface-strong,#fff)',
            'border:1px solid var(--surface-border,rgba(19,32,45,.1))',
            'color:var(--text,#13202d)',
            'display:none',
            'font-weight:700'
        ].join(';');
        document.body.appendChild(el);
        return el;
    }

    function showToast(html, isError) {
        var el = ensureToast();
        el.innerHTML = html;
        el.style.borderColor = isError ? 'rgba(194,54,22,.28)' : 'rgba(17,138,85,.28)';
        el.style.display = 'block';
        clearTimeout(window.__qcWatchlistToastTimer);
        window.__qcWatchlistToastTimer = setTimeout(function () {
            el.style.display = 'none';
        }, 3600);
    }

    window.qcAddToWatchlist = async function (symbol, name, options) {
        var code = normalizeSymbol(symbol);
        if (!code) {
            showToast('股票代码为空，无法加入自选', true);
            return false;
        }
        options = options || {};
        try {
            var response = await fetch('/api/v1/watchlist', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: code })
            });
            var payload = await response.json().catch(function () { return {}; });
            if (!response.ok || (payload.status && payload.status !== 'success')) {
                throw new Error((payload.error && payload.error.message) || payload.message || '加入自选失败');
            }
            showToast(
                '已加入自选：' + esc(name || code) +
                ' <a href="/self-stocks" style="margin-left:8px;color:var(--brand);">查看自选</a>',
                false
            );
            fetch('/api/v1/user/audit-trail', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'watchlist_add',
                    target_type: 'symbol',
                    target_id: code,
                    metadata: { name: name || code, source: options.source || 'quick_action' }
                })
            }).catch(function () {});
            window.dispatchEvent(new CustomEvent('qc:watchlist-added', { detail: { symbol: code, name: name || code } }));
            if (typeof options.onSuccess === 'function') options.onSuccess(payload);
            return true;
        } catch (err) {
            showToast(esc(err.message || '加入自选失败'), true);
            return false;
        }
    };

    window.qcWatchlistButton = function (symbol, name, label, extraClass) {
        return '<button type="button" class="' + esc(extraClass || 'btn-soft btn-sm') +
            '" data-watchlist-add data-symbol="' + esc(String(symbol || '')) +
            '" data-name="' + esc(String(name || '')) + '">' +
            esc(label || '加自选') + '</button>';
    };

    document.addEventListener('click', function (event) {
        var btn = event.target.closest('[data-watchlist-add]');
        if (!btn) return;
        event.stopPropagation();
        window.qcAddToWatchlist(
            btn.getAttribute('data-symbol') || '',
            btn.getAttribute('data-name') || ''
        );
    });
})();
