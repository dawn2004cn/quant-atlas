/**
 * wasm_quant_loader.js — Load and cache the WASM computation kernel.
 *
 * Usage:
 *   const quant = await WasmQuantLoader.load();
 *   const ma5 = quant.calculate_sma(prices, 5);
 *
 * Falls back gracefully (null) when WASM unavailable.
 */
(function (global) {
    'use strict';

    var WASM_URL = global.WASM_QUANT_URL || '/static/wasm/quant_core.wasm';
    var _instance = null;
    var _loading = null;

    var WasmQuantLoader = {
        /** @returns {Promise<object|null>} */
        load: function () {
            if (_instance) return Promise.resolve(_instance);
            if (_loading) return _loading;

            // Feature detect
            if (typeof WebAssembly === 'undefined' || !WebAssembly.instantiateStreaming) {
                console.warn('[WasmQuant] WebAssembly not supported');
                return Promise.resolve(null);
            }

            _loading = fetch(WASM_URL)
                .then(function (res) {
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    return WebAssembly.instantiateStreaming(res);
                })
                .then(function (result) {
                    _instance = result.instance.exports;
                    console.debug('[WasmQuant] kernel loaded, exports:', Object.keys(_instance));
                    return _instance;
                })
                .catch(function (err) {
                    console.warn('[WasmQuant] load failed:', err);
                    _instance = null;
                    return null;
                });

            return _loading;
        },

        /** Run SMA on the main thread or fallback to JS */
        sma: function (data, window) {
            if (!data || !data.length) return [];
            return WasmQuantLoader.load().then(function (mod) {
                if (mod && mod.calculate_sma) {
                    return mod.calculate_sma(new Float64Array(data), window);
                }
                // Fallback JS
                return _jsSMA(data, window);
            });
        },

        /** Run EMA with WASM fallback */
        ema: function (data, window) {
            if (!data || !data.length) return [];
            return WasmQuantLoader.load().then(function (mod) {
                if (mod && mod.calculate_ema) {
                    return mod.calculate_ema(new Float64Array(data), window);
                }
                return _jsEMA(data, window);
            });
        },

        /** Run ATR with WASM fallback */
        atr: function (highs, lows, closes, window) {
            if (!highs || !highs.length) return [];
            return WasmQuantLoader.load().then(function (mod) {
                if (mod && mod.calculate_atr) {
                    return mod.calculate_atr(
                        new Float64Array(highs),
                        new Float64Array(lows),
                        new Float64Array(closes),
                        window
                    );
                }
                return _jsATR(highs, lows, closes, window);
            });
        },

        /** Batch calculate multiple indicators at once */
        batch: function (data, indicators) {
            return WasmQuantLoader.load().then(function (mod) {
                if (mod && mod.batch_calculate) {
                    return mod.batch_calculate(new Float64Array(data), indicators);
                }
                // JS fallback
                return indicators.map(function (name) {
                    switch (name) {
                        case 'sma_5': return _jsSMA(data, 5);
                        case 'sma_10': return _jsSMA(data, 10);
                        case 'sma_20': return _jsSMA(data, 20);
                        case 'ema_5': return _jsEMA(data, 5);
                        case 'ema_10': return _jsEMA(data, 10);
                        case 'ema_20': return _jsEMA(data, 20);
                        case 'zscore_20': return _jsZScore(data, 20);
                        default: return [];
                    }
                });
            });
        },

        /** Check if WASM is available immediately */
        isAvailable: function () { return _instance !== null; },
    };

    // Pure JS fallback implementations
    function _jsSMA(data, window) {
        if (window <= 0 || data.length < window) return data.map(function () { return 0; });
        var result = [];
        for (var i = 0; i < data.length; i++) {
            if (i < window - 1) { result.push(0); continue; }
            var sum = 0;
            for (var j = 0; j < window; j++) sum += data[i - j];
            result.push(Number((sum / window).toFixed(4)));
        }
        return result;
    }

    function _jsEMA(data, window) {
        if (window <= 0 || data.length === 0) return data.map(function () { return 0; });
        var alpha = 2 / (window + 1);
        var result = [data[0]];
        for (var i = 1; i < data.length; i++) {
            result.push(data[i] * alpha + result[i - 1] * (1 - alpha));
        }
        return result;
    }

    function _jsATR(highs, lows, closes, window) {
        var n = Math.min(highs.length, lows.length, closes.length);
        if (n < window + 1) return Array(n).fill(0);
        var tr = [highs[0] - lows[0]];
        for (var i = 1; i < n; i++) {
            var hl = highs[i] - lows[i];
            var hpc = Math.abs(highs[i] - closes[i - 1]);
            var lpc = Math.abs(lows[i] - closes[i - 1]);
            tr.push(Math.max(hl, hpc, lpc));
        }
        // Pad to match input length
        var atr = Array(n).fill(0);
        for (var i = window - 1; i < n; i++) {
            var sum = 0;
            for (var j = 0; j < window; j++) sum += tr[i - j];
            atr[i] = sum / window;
        }
        return atr;
    }

    function _jsZScore(data, window) {
        var result = Array(data.length).fill(0);
        for (var i = window - 1; i < data.length; i++) {
            var slice = data.slice(i + 1 - window, i + 1);
            var mean = slice.reduce(function (a, b) { return a + b; }, 0) / window;
            var variance = slice.reduce(function (s, x) { return s + (x - mean) ** 2; }, 0) / window;
            result[i] = variance > 0 ? (data[i] - mean) / Math.sqrt(variance) : 0;
        }
        return result;
    }

    global.WasmQuantLoader = WasmQuantLoader;
})(window);
