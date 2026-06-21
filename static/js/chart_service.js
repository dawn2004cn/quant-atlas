/**
 * QCChartService — unified chart abstraction.
 *
 * Wraps:
 *  - Lightweight Charts (kline / volume)
 *  - ECharts (equity / radar / bar)
 *  - Three.js (3D topology — placeholder)
 *  - React Flow (graph — placeholder)
 *
 * All instances tracked; page unload auto-destroys.
 */
(function (global) {
    'use strict';

    var _instances = [];
    var _containerMap = new WeakMap();

    function _register(container, api) {
        _instances.push({ container: container, api: api, created: Date.now() });
        _containerMap.set(container, api);
    }

    function _unregister(container) {
        _instances = _instances.filter(function (item) {
            return item.container !== container;
        });
        _containerMap.delete(container);
    }

    function _get(container) {
        return _containerMap.get(container);
    }

    function destroyAll() {
        _instances.forEach(function (item) {
            try {
                if (item.api && typeof item.api.destroy === 'function') {
                    item.api.destroy();
                }
            } catch (_) {
                /* ignore */
            }
        });
        _instances = [];
        _containerMap = new WeakMap();
    }

    function destroy(container) {
        var entry = _get(container);
        if (entry && typeof entry.destroy === 'function') {
            try {
                entry.destroy();
            } catch (_) {
                /* ignore */
            }
        }
        _unregister(container);
    }

    // ---- Lightweight Charts (kline) ----
    function _chartColors() {
        var cs = getComputedStyle(document.documentElement);
        var getVar = function(name) {
            return cs.getPropertyValue(name).trim() || '';
        };
        return {
            bg: getVar('--bg') || '#f8fafc',
            text: getVar('--text') || '#0f172a',
            positive: getVar('--positive') || '#10b981',
            negative: getVar('--negative') || '#ef4444',
            border: getVar('--surface-border') || 'rgba(16,63,145,0.08)',
        };
    }

    function createKline(container, seriesData, opts) {
        opts = opts || {};
        var LightweightCharts = global.LightweightCharts;
        if (!LightweightCharts) {
            return { error: 'LightweightCharts not loaded' };
        }
        try {
            var colors = _chartColors();
            var chart = LightweightCharts.createChart(container, Object.assign({}, opts, {
                width: container.clientWidth,
                height: container.clientHeight || 400,
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: colors.text,
                },
                grid: {
                    vertLines: { color: colors.border },
                    horzLines: { color: colors.border },
                },
                crosshair: { mode: 1 },
                rightPriceScale: { borderColor: colors.border },
                timeScale: { borderColor: colors.border, timeVisible: true },
            }));
            var candleSeriesOpts = Object.assign({}, opts.series || {}, {
                upColor: colors.positive,
                downColor: colors.negative,
                borderVisible: false,
                wickUpColor: colors.positive,
                wickDownColor: colors.negative,
            });
            var candleSeries = chart.addCandlestickSeries(candleSeriesOpts);
            if (Array.isArray(seriesData)) {
                candleSeries.setData(seriesData);
            }
            var api = {
                chart: chart,
                series: candleSeries,
                update: function (row) { candleSeries.update(row); },
                resize: function (w, h) { chart.applyOptions({ width: w, height: h }); },
                destroy: function () { chart.remove(); },
            };
            _register(container, api);
            return api;
        } catch (e) {
            return { error: String(e) };
        }
    }

    // ---- ECharts (equity / radar / bar) ----
    function createECharts(container, option, opts) {
        opts = opts || {};
        var echarts = global.echarts;
        if (!echarts) {
            return { error: 'echarts not loaded' };
        }
        try {
            // Auto-detect theme from CSS variables (respects [data-theme="dark"])
            var colors = _chartColors();
            var themeName = colors.bg.startsWith('#0') ? 'dark' : 'light';
            var chart = echarts.init(container, themeName, { renderer: opts.renderer || 'canvas' });
            var defaultOption = {
                backgroundColor: 'transparent',
                textStyle: { fontFamily: 'Inter, ui-sans-serif, system-ui' },
                animation: true,
            };
            chart.setOption(Object.assign({}, defaultOption, option), true);
            var api = {
                chart: chart,
                setOption: function (o, notMerge) { chart.setOption(o, notMerge); },
                resize: function () { chart.resize(); },
                destroy: function () { chart.dispose(); },
            };
            _register(container, api);
            return api;
        } catch (e) {
            return { error: String(e) };
        }
    }

    // ---- Three.js placeholder (3D topology) ----
    function create3D(container, opts) {
        return { error: 'Three.js topology viewer not yet implemented' };
    }

    // ---- React Flow placeholder (graph) ----
    function createFlow(container, nodes, edges, opts) {
        return { error: 'React Flow graph viewer not yet implemented' };
    }

    function addStopLossLine(api, price, opts) {
        // Add a dashed horizontal line at the stop-loss price on an existing kline chart
        opts = opts || {};
        if (!api || !api.chart) return { error: 'No chart API' };
        try {
            var lineOpts = {
                color: opts.color || "#ef4444",
                lineWidth: opts.lineWidth || 2,
                lineStyle: 2,  // dashed
                lastValueVisible: true,
                priceLineVisible: false,
                title: opts.title || "止损线",
            };
            var lineSeries = api.chart.addLineSeries(lineOpts);
            var data = [];
            var timeRange = api.chart.timeScale().getVisibleRange();
            if (timeRange && timeRange.from && timeRange.to) {
                data.push({ time: timeRange.from, value: price });
                data.push({ time: timeRange.to, value: price });
            } else {
                var now = Math.floor(Date.now() / 1000);
                data.push({ time: now - 86400 * 30, value: price });
                data.push({ time: now, value: price });
            }
            lineSeries.setData(data);
            return { lineSeries: lineSeries };
        } catch (e) {
            return { error: String(e) };
        }
    }

    function addPreflightLines(api, stopLoss, takeProfit, atrStop) {
        // Convenience wrapper: add both stop-loss and take-profit lines
        var results = {};
        if (stopLoss != null) {
            results.stopLoss = addStopLossLine(api, stopLoss, { color: "#ef4444", title: "硬止损" });
        }
        if (atrStop != null) {
            results.atrStop = addStopLossLine(api, atrStop, { color: "#f59e0b", title: "ATR追踪", lineStyle: 2 });
        }
        if (takeProfit != null) {
            results.takeProfit = addStopLossLine(api, takeProfit, { color: "#10b981", title: "止盈", lineStyle: 1 });
        }
        return results;
    }

    global.QCChartService = {
        createKline: createKline,
        addStopLossLine: addStopLossLine,
        addPreflightLines: addPreflightLines,
        createECharts: createECharts,
        create3D: create3D,
        createFlow: createFlow,
        destroy: destroy,
        destroyAll: destroyAll,
        get: _get,
        instances: _instances,
    };
})(window);
