/**
 * User-center UX helpers: decision brief, trade-plan adopt, freshness, active jobs.
 */
(function (global) {
    'use strict';

    function escHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function unwrapData(json) {
        if (!json || typeof json !== 'object') return json;
        if (json.data !== undefined) return json.data;
        return json;
    }

    function freshnessLevel(payload) {
        if (!payload || typeof payload !== 'object') return 'unknown';
        if (payload.freshness_level) return payload.freshness_level;
        if (payload.freshness && payload.freshness.freshness_level) return payload.freshness.freshness_level;
        if (payload.is_realtime === true) return 'realtime';
        if (payload.is_realtime === false) return 'stale';
        return 'unknown';
    }

    function freshnessTimestamp(payload) {
        if (!payload) return '';
        return (
            payload.data_timestamp ||
            (payload.freshness && payload.freshness.data_timestamp) ||
            ''
        );
    }

    const QAUserCenter = {
        escHtml: escHtml,

        renderFreshnessStrip: function (el, payload, opts) {
            if (!el) return;
            const level = freshnessLevel(payload);
            const ts = freshnessTimestamp(payload);
            if (!ts && level === 'unknown') {
                el.style.display = 'none';
                return;
            }
            el.className = 'qc-freshness-strip ' + level;
            const labels = {
                realtime: '行情实时',
                delayed: '行情延迟',
                stale: '行情可能过期',
                unknown: '行情时间未知',
            };
            let text = (opts && opts.prefix ? opts.prefix + ' · ' : '') + (labels[level] || labels.unknown);
            if (ts) text += ' · ' + String(ts).replace('T', ' ').replace('+00:00', ' UTC');
            if (level === 'stale' || level === 'unknown') {
                text += ' — 请勿仅凭过期报价决策';
            }
            el.textContent = text;
            el.style.display = 'block';
        },

        loadPanoramaFreshness: async function (market, el) {
            if (!el) return null;
            try {
                const res = await fetch(
                    '/api/v1/markets/' + encodeURIComponent(market || 'CN') + '/panorama',
                    { credentials: 'same-origin' }
                );
                const json = await res.json();
                const pano = unwrapData(json);
                const resource = pano.panorama || pano;
                QAUserCenter.renderFreshnessStrip(el, resource, { prefix: '市场全景' });
                return resource;
            } catch (e) {
                el.style.display = 'none';
                return null;
            }
        },

        loadDecisionBrief: function (symbol, market, opts) {
            const sym = String(symbol || '').trim();
            const mkt = String(market || 'CN').trim().toUpperCase();
            if (!sym) {
                return Promise.reject(new Error('symbol_required'));
            }
            const params = new URLSearchParams();
            if (opts && opts.role) params.set('role', opts.role);
            params.set('timeline_limit', String((opts && opts.timeline_limit) || 30));
            const qs = params.toString();
            const url =
                '/api/v1/stocks/' +
                encodeURIComponent(mkt) +
                '/' +
                encodeURIComponent(sym) +
                '/decision-brief' +
                (qs ? '?' + qs : '');
            return fetch(url, { credentials: 'same-origin' })
                .then(function (res) { return res.json(); })
                .then(function (json) {
                    if (json.status && json.status !== 'success') {
                        throw new Error(json.message || 'decision_brief_failed');
                    }
                    return unwrapData(json);
                });
        },

        adoptTradePlan: async function (body) {
            const payload = Object.assign(
                {
                    account_equity: 100000,
                    cash_available: 100000,
                    risk_per_trade_pct: 1,
                    max_position_pct: 15,
                },
                body || {}
            );
            if (!payload.symbol) throw new Error('symbol_required');
            if (!payload.market) payload.market = 'CN';
            const res = await fetch('/api/v1/trade-plan/adopt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(payload),
            });
            const json = await res.json();
            if (!res.ok || (json.status && json.status !== 'success')) {
                throw new Error((json && json.message) || 'adopt_failed');
            }
            return unwrapData(json);
        },

        loadActiveJobs: async function (limit) {
            try {
                const res = await fetch(
                    '/api/v1/system/active-jobs?limit=' + encodeURIComponent(String(limit || 10)),
                    { credentials: 'same-origin' }
                );
                const json = await res.json();
                const data = unwrapData(json);
                return (data && data.items) || [];
            } catch (e) {
                return [];
            }
        },

        runRegisteredTask: async function (taskName, params, progressOpts) {
            const opts = progressOpts || {};
            const el =
                typeof opts.element === 'string'
                    ? document.querySelector(opts.element)
                    : opts.element;
            const body = { task_name: taskName, params: params || {} };
            const res = await fetch('/api/v1/tasks/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const json = await res.json();
            if (!res.ok || (json.status && json.status !== 'success')) {
                throw new Error((json && json.message) || 'task_run_failed');
            }
            const data = unwrapData(json);
            const taskId = data && (data.task_id || data.id);
            if (taskId && el && global.QCTaskFeedback) {
                global.QCTaskFeedback.watch(taskId, {
                    element: el,
                    taskName: taskName,
                    intervalMs: opts.intervalMs || 2000,
                    onComplete: opts.onComplete,
                    onError: opts.onError,
                });
            }
            if (typeof opts.onStarted === 'function') {
                opts.onStarted(data);
            }
            return data;
        },

        fetchMarketQuotesFreshness: async function (market, codes) {
            const list = (codes || []).filter(Boolean).slice(0, 40);
            const map = {};
            if (!list.length) return map;
            const mkt = (market || 'CN').toUpperCase();
            const qs = new URLSearchParams();
            list.forEach(function (c) {
                qs.append('symbol', String(c).replace(/\.(SH|SZ|HK)$/i, ''));
            });
            try {
                const res = await fetch(
                    '/api/v1/markets/' + encodeURIComponent(mkt) + '/quotes?' + qs.toString(),
                    { credentials: 'same-origin' }
                );
                const json = await res.json();
                const rows = unwrapData(json);
                const arr = Array.isArray(rows)
                    ? rows
                    : (rows && (rows.stocks || rows.items)) || [];
                arr.forEach(function (row) {
                    const raw = row.symbol || row.code || row.ticker;
                    if (!raw) return;
                    const code = String(raw).replace(/\.(SH|SZ|HK)$/i, '');
                    map[code] = row;
                    map[String(raw)] = row;
                });
            } catch (e) {
                /* ignore */
            }
            return map;
        },

        renderHotSectorFreshness: function (el, meta) {
            if (!el) return;
            const mode = (meta && meta.source_mode) || (meta && meta.source) || 'auto';
            if (meta && (meta.data_timestamp || meta.is_realtime != null || meta.freshness)) {
                QAUserCenter.renderFreshnessStrip(el, meta, {
                    prefix: '热点板块 · ' + mode,
                });
                return;
            }
            const snap =
                (meta && meta.snapshot_at) ||
                (meta && meta.updated_at) ||
                '';
            let level = 'unknown';
            if (mode === 'live') {
                level = 'realtime';
            } else if (snap) {
                const t = Date.parse(String(snap).replace(' ', 'T'));
                if (!isNaN(t)) {
                    const ageH = (Date.now() - t) / 3600000;
                    if (ageH > 24) level = 'stale';
                    else if (ageH > 2) level = 'delayed';
                    else level = 'realtime';
                } else {
                    level = 'delayed';
                }
            }
            QAUserCenter.renderFreshnessStrip(
                el,
                { freshness_level: level, data_timestamp: snap },
                { prefix: '热点板块 · ' + mode }
            );
        },

        mountActiveJobsPanel: async function (containerId, limit) {
            const box = document.getElementById(containerId);
            if (!box) return;
            const items = await QAUserCenter.loadActiveJobs(limit || 6);
            QAUserCenter.renderActiveJobsMini(box, items);
        },

        renderDecisionBriefMini: function (bodyEl, brief, freshnessEl) {
            if (!bodyEl || !brief) return;
            const header = brief.header || {};
            const ts = brief.timeline_summary || {};
            const warnings = (brief.warnings || []).slice(0, 4);
            const quoteComp = (brief.components || []).find(function (c) {
                return c && c.type === 'quote_strip';
            });
            const payload = (quoteComp && quoteComp.payload) || header;
            let html =
                '<div style="font-weight:800;font-size:1rem;">' +
                escHtml(header.name || brief.symbol || '') +
                ' · ' +
                escHtml(String(header.price != null ? header.price : '--'));
            if (header.change_pct != null && !isNaN(Number(header.change_pct))) {
                html +=
                    ' <span style="color:var(--brand);">(' +
                    Number(header.change_pct).toFixed(2) +
                    '%)</span>';
            }
            html += '</div>';
            if (header.industry || header.chain_name) {
                html +=
                    '<div class="text-muted" style="font-size:0.82rem;margin-top:4px;">' +
                    escHtml([header.industry, header.chain_name].filter(Boolean).join(' · ')) +
                    '</div>';
            }
            if (ts.count) {
                html +=
                    '<div class="text-muted" style="font-size:0.82rem;margin-top:6px;">归因时间轴 ' +
                    escHtml(String(ts.count)) +
                    ' 条</div>';
            }
            warnings.forEach(function (w) {
                html +=
                    '<div style="font-size:0.82rem;margin-top:4px;color:var(--negative);">' +
                    escHtml(String(w)) +
                    '</div>';
            });
            bodyEl.innerHTML = html;
            if (freshnessEl && payload) {
                QAUserCenter.renderFreshnessStrip(freshnessEl, payload, { prefix: '行情' });
            }
        },

        runBasicDataRefresh: async function (kind, progressOpts) {
            const opts = progressOpts || {};
            const el =
                typeof opts.element === 'string'
                    ? document.querySelector(opts.element)
                    : opts.element;
            const res = await fetch('/api/v1/market/basic-data/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ kind: kind || 'all' }),
            });
            const json = await res.json();
            const data = unwrapData(json);
            if (
                data &&
                data.mode === 'async' &&
                data.task_id &&
                global.QCTaskFeedback &&
                el
            ) {
                global.QCTaskFeedback.watch(data.task_id, {
                    element: el,
                    taskName: 'app.tasks.market_tasks.refresh_basic_market_data',
                    onComplete: opts.onComplete,
                });
            } else if (typeof opts.onComplete === 'function') {
                opts.onComplete(data);
            }
            if (typeof opts.onStarted === 'function') opts.onStarted(data);
            return data;
        },

        runDecisionFlowSelfCheck: async function (container, options) {
            const box =
                typeof container === 'string' ? document.getElementById(container) : container;
            if (!box) return [];
            const opts = options || {};
            const sym = String(opts.symbol || '600519').trim();
            const market = String(opts.market || 'CN').toUpperCase();
            box.innerHTML = '<div class="text-muted" style="font-size:0.85rem;">正在自检决策链路…</div>';
            let probes = opts.probes;
            if (!probes || !probes.length) {
                try {
                    const cRes = await fetch(
                        '/api/v1/ux/decision-flow?market=' +
                            encodeURIComponent(market) +
                            '&symbol=' +
                            encodeURIComponent(sym),
                        { credentials: 'same-origin' }
                    );
                    const cJson = await cRes.json();
                    const contract = unwrapData(cJson);
                    probes = (contract && contract.self_check_probes) || [];
                } catch (e) {
                    box.innerHTML =
                        '<div style="color:var(--negative);">无法加载自检清单：' +
                        escHtml(e.message || String(e)) +
                        '</div>';
                    return [];
                }
            }
            function hasExpectedKeys(data, keys) {
                if (!keys || !keys.length) return true;
                for (let i = 0; i < keys.length; i++) {
                    const key = keys[i];
                    if (data && data[key] !== undefined) return true;
                    if (data && data.panorama && data.panorama[key] !== undefined) return true;
                }
                return false;
            }
            const results = [];
            for (let pi = 0; pi < probes.length; pi++) {
                const p = probes[pi];
                const row = { id: p.id, label: p.label || p.id, ok: false, detail: '' };
                try {
                    const res = await fetch(p.url, { credentials: 'same-origin' });
                    const json = await res.json();
                    const data = unwrapData(json);
                    row.ok =
                        res.ok && (!json.status || json.status === 'success') && hasExpectedKeys(data, p.expect_keys);
                    row.detail = row.ok ? 'OK' : row.detail || '响应异常或缺少字段';
                } catch (err) {
                    row.detail = err.message || String(err);
                }
                results.push(row);
            }
            const pass = results.filter(function (r) {
                return r.ok;
            }).length;
            box.innerHTML =
                '<div style="font-weight:800;margin-bottom:8px;">自检 ' +
                pass +
                '/' +
                results.length +
                ' 通过</div>' +
                results
                    .map(function (r) {
                        return (
                            '<div style="padding:6px 0;font-size:0.85rem;border-bottom:1px solid rgba(0,0,0,0.06);">' +
                            '<span style="font-weight:800;color:' +
                            (r.ok ? 'var(--positive)' : 'var(--negative)') +
                            ';">' +
                            (r.ok ? '✓' : '✗') +
                            '</span> ' +
                            escHtml(r.label) +
                            ' <span class="text-muted">' +
                            escHtml(r.detail) +
                            '</span></div>'
                        );
                    })
                    .join('');
            return results;
        },

        renderEvidenceFeedFreshness: function (el, meta, prefix) {
            if (!el || !meta) return;
            QAUserCenter.renderFreshnessStrip(el, meta, { prefix: prefix || '数据' });
        },

        renderUiSurfacesTable: function (tbody, surfaces) {
            if (!tbody) return;
            const rows = surfaces || [];
            if (!rows.length) {
                tbody.innerHTML =
                    '<tr><td colspan="4" class="fit-desc">暂无 ui_surfaces 数据</td></tr>';
                return;
            }
            tbody.innerHTML = rows
                .map(function (s) {
                    let path = String(s.path || '/');
                    let href = path;
                    if (path.indexOf('{symbol}') >= 0) {
                        href = path.replace('{symbol}', '600519') + '?m=CN#decision-brief-strip';
                    }
                    const feats = (s.features || []).join(' · ');
                    return (
                        '<tr><td class="fit-name">' +
                        escHtml(s.page || '') +
                        '</td><td class="fit-desc">' +
                        escHtml(feats) +
                        '</td><td><a class="badge-soft" href="' +
                        escHtml(href) +
                        '">' +
                        escHtml(path) +
                        '</a></td><td><span class="status-chip status-integrate">已落地</span></td></tr>'
                    );
                })
                .join('');
        },

        loadDecisionFlowContract: function (market, symbol) {
            const mkt = String(market || 'CN').toUpperCase();
            const sym = String(symbol || '600519').trim();
            return fetch(
                '/api/v1/ux/decision-flow?market=' +
                    encodeURIComponent(mkt) +
                    '&symbol=' +
                    encodeURIComponent(sym),
                { credentials: 'same-origin' }
            )
                .then(function (res) {
                    return res.json();
                })
                .then(function (json) {
                    if (json.status && json.status !== 'success') {
                        throw new Error(json.message || 'contract_failed');
                    }
                    return unwrapData(json);
                });
        },

        stockDetailBriefHref: function (symbol, market) {
            const sym = String(symbol || '').trim();
            const mkt = String(market || 'CN').trim().toUpperCase();
            return (
                '/stock/' +
                encodeURIComponent(sym) +
                '?m=' +
                encodeURIComponent(mkt) +
                '#decision-brief-strip'
            );
        },

        freshnessBadgeHtml: function (row) {
            if (!row) return '';
            const ts = row.data_timestamp || row.updated_at || row.quote_time;
            const rt = row.is_realtime;
            let cls = 'qc-freshness-badge qc-freshness-stale';
            let label = '未知';
            if (rt === true || rt === 1) {
                cls = 'qc-freshness-badge qc-freshness-live';
                label = '实时';
            } else if (ts) {
                cls = 'qc-freshness-badge qc-freshness-delayed';
                label = '延时';
            }
            const tip = ts ? escHtml(String(ts).slice(0, 19)) : '';
            return (
                '<span class="' +
                cls +
                '" title="' +
                tip +
                '">' +
                label +
                '</span>'
            );
        },

        loadRefactorStatus: function () {
            return fetch('/api/v1/retail-assistant/refactor-status', {
                credentials: 'same-origin',
            })
                .then(function (res) {
                    return res.json();
                })
                .then(function (json) {
                    if (json.status && json.status !== 'success') {
                        throw new Error(json.message || 'refactor_status_failed');
                    }
                    return unwrapData(json);
                });
        },

        renderRefactorStatus: function (container, data) {
            const box =
                typeof container === 'string' ? document.getElementById(container) : container;
            if (!box) return;
            const pillars = (data && data.pillars) || [];
            if (!pillars.length) {
                box.innerHTML = '<div class="text-muted text-sm">暂无 refacter 对照数据</div>';
                return;
            }
            function statusChip(st) {
                const s = String(st || 'unknown').toLowerCase();
                let color = 'var(--muted)';
                if (s === 'implemented') color = 'var(--positive)';
                else if (s === 'partial') color = '#b45309';
                else if (s === 'planned') color = 'var(--negative)';
                return (
                    '<span style="font-weight:800;font-size:0.72rem;color:' +
                    color +
                    ';">' +
                    escHtml(st || '—') +
                    '</span>'
                );
            }
            box.innerHTML =
                (data.source_doc
                    ? '<div class="text-muted text-sm" style="margin-bottom:10px;">来源 ' +
                      escHtml(data.source_doc) +
                      (data.generated_at ? ' · ' + escHtml(data.generated_at) : '') +
                      '</div>'
                    : '') +
                pillars
                    .map(function (pillar) {
                        const items = pillar.items || [];
                        return (
                            '<div style="margin-bottom:14px;padding:12px;border-radius:14px;border:1px solid rgba(0,0,0,0.06);">' +
                            '<div style="font-weight:800;margin-bottom:8px;">' +
                            escHtml(pillar.title || pillar.id || '') +
                            '</div>' +
                            items
                                .map(function (it) {
                                    const entry = it.entry
                                        ? String(it.entry).indexOf('/') === 0
                                            ? '<a class="badge-soft" href="' +
                                              escHtml(it.entry) +
                                              '">' +
                                              escHtml(it.entry) +
                                              '</a>'
                                            : '<span class="text-muted" style="font-size:0.75rem;">' +
                                              escHtml(it.entry) +
                                              '</span>'
                                        : '';
                                    return (
                                        '<div style="padding:5px 0;font-size:0.82rem;border-bottom:1px solid rgba(0,0,0,0.04);">' +
                                        '<span style="font-weight:700;">' +
                                        escHtml(it.name || '') +
                                        '</span> ' +
                                        statusChip(it.status) +
                                        (entry ? '<div style="margin-top:4px;">' + entry + '</div>' : '') +
                                        '</div>'
                                    );
                                })
                                .join('') +
                            '</div>'
                        );
                    })
                    .join('') +
                (data.scheduled_jobs && data.scheduled_jobs.length
                    ? '<div style="margin-top:12px;font-size:0.82rem;"><strong>定时任务</strong>' +
                      data.scheduled_jobs
                          .map(function (j) {
                              return (
                                  '<div class="text-muted" style="padding:4px 0;">' +
                                  escHtml(j.id || '') +
                                  ' · ' +
                                  escHtml(j.schedule || '') +
                                  (j.manual ? ' · ' + escHtml(j.manual) : '') +
                                  '</div>'
                              );
                          })
                          .join('') +
                      '</div>'
                    : '');
        },

        fetchLifecycleSettings: function () {
            return fetch('/api/v1/user/lifecycle', { credentials: 'same-origin' })
                .then(function (res) {
                    return res.json();
                })
                .then(function (json) {
                    if (json.status && json.status !== 'success') {
                        throw new Error(json.message || 'lifecycle_failed');
                    }
                    return unwrapData(json);
                });
        },

        psychologyAlertsEnabled: function (settings) {
            const notifications = (settings && settings.notifications) || {};
            return notifications.psychology_alerts !== false;
        },

        updateNotificationPreferences: function (patch) {
            return fetch('/api/v1/user/notification-preferences', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(patch || {}),
            })
                .then(function (res) {
                    return res.json();
                })
                .then(function (json) {
                    if (json.status && json.status !== 'success') {
                        throw new Error(json.message || 'notification_prefs_failed');
                    }
                    return unwrapData(json);
                });
        },

        fetchPsychologyStatus: function () {
            return fetch('/api/v1/retail-assistant/psychology-status', {
                credentials: 'same-origin',
            })
                .then(function (res) {
                    return res.json();
                })
                .then(function (json) {
                    if (json.status && json.status !== 'success') {
                        throw new Error(json.message || 'psychology_status_failed');
                    }
                    return unwrapData(json);
                });
        },

        mountPsychologyMiniStrip: function (containerId) {
            const box =
                typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
            if (!box) return Promise.resolve(null);
            box.style.display = 'none';
            return QAUserCenter.fetchPsychologyStatus()
                .then(function (st) {
                    if (!st || st.status !== 'warning' || !(st.alert_count > 0)) {
                        box.style.display = 'none';
                        box.innerHTML = '';
                        return st;
                    }
                    const msg = st.top_message || '检测到情绪化操作倾向';
                    const links = st.links || {};
                    box.className = 'qc-ux-banner qc-ux-banner--danger';
                    box.style.display = 'block';
                    box.style.marginBottom = '12px';
                    box.innerHTML =
                        '<div class="qc-ux-banner__title" style="font-size:0.9rem;">心理卫士（账户行为）</div>' +
                        '<div class="qc-ux-banner__body" style="font-size:0.82rem;">' +
                        escHtml(msg) +
                        ' · 非本股专属诊断，反映您近期加自选/采纳等操作模式。' +
                        '</div>' +
                        '<a class="btn-soft btn-sm" href="' +
                        escHtml(links.detail || '/retail-assistant#psychologyBox') +
                        '">散户助手</a> ' +
                        '<a class="btn-soft btn-sm" href="' +
                        escHtml(links.messages || '/message-center?filter=psychology') +
                        '">消息</a>';
                    return st;
                })
                .catch(function () {
                    box.style.display = 'none';
                    return null;
                });
        },

        runPsychologyScan: function (options) {
            const opts = options || {};
            const notify = !!opts.notify;
            const qs = notify ? '?notify=1' : '';
            return fetch('/api/v1/retail-assistant/psychology-scan' + qs, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notify: notify }),
            })
                .then(function (res) {
                    return res.json();
                })
                .then(function (json) {
                    if (json.status && json.status !== 'success') {
                        throw new Error(json.message || 'psychology_scan_failed');
                    }
                    return unwrapData(json);
                });
        },

        mountPsychologyBanner: function (containerId, options) {
            const box =
                typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
            if (!box) return Promise.resolve(null);
            const opts = options || {};
            box.style.display = 'none';
            return QAUserCenter.fetchPsychologyStatus()
                .then(function (st) {
                    if (!st || st.status !== 'warning' || !(st.alert_count > 0)) {
                        box.style.display = 'none';
                        box.innerHTML = '';
                        return st;
                    }
                    const msg = st.top_message || '检测到情绪化操作倾向';
                    const sug = st.top_suggestion || (st.recommendations && st.recommendations[0]) || '';
                    const links = st.links || {};
                    box.className = opts.bannerClass || 'qc-ux-banner qc-ux-banner--danger';
                    box.style.display = 'block';
                    box.innerHTML =
                        '<div class="qc-ux-banner__title">心理卫士提醒</div>' +
                        '<div class="qc-ux-banner__body">' +
                        escHtml(msg) +
                        (sug ? '<br><span style="opacity:0.9;">' + escHtml(sug) + '</span>' : '') +
                        '</div>' +
                        '<a class="btn-soft btn-sm" href="' +
                        escHtml(links.detail || '/retail-assistant#psychologyBox') +
                        '">查看详情</a> ' +
                        '<a class="btn-soft btn-sm" href="' +
                        escHtml(links.messages || '/message-center?filter=psychology') +
                        '">消息中心</a>';
                    return st;
                })
                .catch(function () {
                    box.style.display = 'none';
                    return null;
                });
        },

        mountRefactorStatusPanel: function (containerId) {
            const box = document.getElementById(containerId);
            if (!box || !window.QAUserCenter) return Promise.resolve(null);
            box.innerHTML = '<div class="text-muted text-sm">正在加载 refacter 对照…</div>';
            return QAUserCenter.loadRefactorStatus()
                .then(function (data) {
                    QAUserCenter.renderRefactorStatus(box, data);
                    return data;
                })
                .catch(function (e) {
                    box.innerHTML =
                        '<div style="color:var(--negative);font-size:0.85rem;">加载失败：' +
                        escHtml(e.message || String(e)) +
                        '</div>';
                    return null;
                });
        },

        loadBeatSyncOps: async function (limit) {
            const cap = Math.max(1, Math.min(Number(limit) || 5, 12));
            const [hRes, histRes] = await Promise.all([
                fetch('/api/v1/data/timeseries-health', { credentials: 'same-origin' }),
                fetch(
                    '/api/v1/data/timeseries-sync-history?limit=' +
                        cap +
                        '&source=celery_beat',
                    { credentials: 'same-origin' }
                ),
            ]);
            const health = unwrapData(await hRes.json());
            const hist = unwrapData(await histRes.json());
            return {
                health: health || {},
                runs: (hist && hist.runs) || (health && health.celery_beat && health.celery_beat.recent_beat_runs) || [],
            };
        },

        renderBeatSyncMini: function (box, payload) {
            if (!box) return;
            const health = (payload && payload.health) || {};
            const beat = health.celery_beat || {};
            const qdb = health.questdb || {};
            const runs = (payload && payload.runs) || [];
            const rows = ((health.ohlcv_tables || {}).questdb_rows);
            const chips = [];
            if (beat.enabled) {
                let beatLabel = beat.schedule_label || '16:35';
                if (beat.sync_in_progress) {
                    const pct = (beat.sync_progress && beat.sync_progress.percent) || 0;
                    beatLabel += ' · 同步中 ' + pct + '%';
                } else if (beat.last_beat_run_at) {
                    beatLabel +=
                        ' · 上次 ' +
                        String(beat.last_beat_run_at).slice(0, 16) +
                        (beat.last_beat_run_ok ? ' ✓' : ' ✗');
                }
                chips.push(beatLabel);
            } else {
                chips.push('Beat 关闭');
            }
            if (qdb.enabled) {
                chips.push(
                    (qdb.connected ? 'QuestDB 在线' : 'QuestDB 离线') +
                        (rows != null ? ' · ' + Number(rows).toLocaleString() + ' 行' : '')
                );
            }
            const qmt = ((health.execution || {}).qmt) || {};
            if (qmt.execution_mode) {
                chips.push('QMT ' + qmt.execution_mode);
            }
            let html =
                '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;">' +
                chips
                    .map(function (c) {
                        return (
                            '<span style="padding:4px 10px;border-radius:999px;font-size:0.78rem;font-weight:700;background:rgba(16,63,145,0.06);">' +
                            escHtml(c) +
                            '</span>'
                        );
                    })
                    .join('') +
                '</div>';
            if (runs.length) {
                html +=
                    '<div style="font-size:0.82rem;font-weight:800;margin-bottom:6px;">Beat 近 ' +
                    runs.length +
                    ' 次</div>' +
                    runs
                        .map(function (r) {
                            const ok = r.ok ? '✓' : '✗';
                            const rowsW =
                                r.questdb_rows_written != null
                                    ? ' +' + r.questdb_rows_written
                                    : '';
                            return (
                                '<div style="padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06);font-size:0.8rem;">' +
                                '<span style="font-weight:700;">' +
                                escHtml(String(r.recorded_at || '').slice(0, 19)) +
                                '</span> ' +
                                ok +
                                rowsW +
                                (r.mode ? ' · ' + escHtml(r.mode) : '') +
                                '</div>'
                            );
                        })
                        .join('');
            } else {
                html +=
                    '<div class="text-muted" style="font-size:0.8rem;">尚无 celery_beat 同步记录</div>';
            }
            html +=
                '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">' +
                '<a class="btn-soft btn-sm" href="/observability">观测台</a>' +
                '<a class="btn-soft btn-sm" href="/data-lake-health">数据湖健康</a>' +
                '</div>';
            box.innerHTML = html;
        },

        mountBeatSyncMiniPanel: function (containerId, limit) {
            const box = document.getElementById(containerId);
            if (!box) return Promise.resolve(null);
            box.innerHTML = '<div class="text-muted text-sm">正在加载 Beat 同步状态…</div>';
            return QAUserCenter.loadBeatSyncOps(limit)
                .then(function (payload) {
                    QAUserCenter.renderBeatSyncMini(box, payload);
                    return payload;
                })
                .catch(function (e) {
                    box.innerHTML =
                        '<div style="color:var(--negative);font-size:0.85rem;">加载失败：' +
                        escHtml(e.message || String(e)) +
                        '</div>';
                    return null;
                });
        },

        renderActiveJobsMini: function (container, items) {
            if (!container) return;
            if (!items || !items.length) {
                container.innerHTML =
                    '<span class="text-muted text-sm">当前无进行中的后台任务</span>';
                return;
            }
            container.innerHTML = items
                .map(function (j) {
                    const pct =
                        j.feedback && j.feedback.percent != null ? j.feedback.percent : '--';
                    const msg =
                        (j.feedback && j.feedback.message) || j.last_detail || '';
                    return (
                        '<div style="padding:6px 0;border-bottom:1px solid rgba(0,0,0,0.06);">' +
                        '<div style="font-weight:700;font-size:0.82rem;">' +
                        escHtml(j.label || j.task_name || j.task_id) +
                        '</div>' +
                        '<div class="text-muted" style="font-size:0.72rem;">进度 ' +
                        pct +
                        '% · ' +
                        escHtml(String(msg).slice(0, 60)) +
                        '</div></div>'
                    );
                })
                .join('');
        },
    };

    global.QAUserCenter = QAUserCenter;
})(typeof window !== 'undefined' ? window : this);
