/**
 * alpha_whisper.js — Non-intrusive Alpha-Whisper overlay engine
 *
 * Adds subtle "energy field" visualization to chart area based on
 * strategy confidence changes. Updates are low-frequency to avoid
 * visual noise.
 *
 * Depends on: QCStateBus, LightweightCharts (if available)
 *
 * Usage:
 *   AlphaWhisper.init({ containerId: "stockChart" });
 *   AlphaWhisper.whisper(symbol, confidence, message);
 */
(function (global) {
    "use strict";

    var DEFAULT_OPTIONS = {
        containerId: "stockChart",
        maxHistory: 20,
        updateIntervalMs: 5000,
        fadeDelayMs: 3000,
    };

    var _opts = {};
    var _history = {};
    var _lastUpdate = 0;
    var _animFrame = null;

    function getOpts() {
        return Object.assign({}, DEFAULT_OPTIONS, _opts);
    }

    var AlphaWhisper = {
        init: function (options) {
            _opts = Object.assign({}, DEFAULT_OPTIONS, options || {});
            _history = {};
            _lastUpdate = 0;

            // Listen for QCStateBus scanner events
            if (global.QCStateBus) {
                global.QCStateBus.subscribe("scanner.last_anomaly", function (payload) {
                    if (payload && payload.symbol) {
                        AlphaWhisper.whisper(payload.symbol, 0.65, payload.reason || "技术信号异常");
                    }
                });
            }

            // Listen for persona mask to adapt whisper intensity
            document.addEventListener("qa:persona-mask-applied", function () {
                // Lower frequency for novice users
                console.debug("[AlphaWhisper] persona-aware adaptation");
            });

            console.debug("[AlphaWhisper] initialized");
        },

        whisper: function (symbol, confidence, message) {
            var now = Date.now();
            if (now - _lastUpdate < getOpts().updateIntervalMs) return;
            _lastUpdate = now;

            if (!_history[symbol]) {
                _history[symbol] = [];
            }
            _history[symbol].push({
                time: now,
                confidence: Math.max(0, Math.min(1, confidence || 0.5)),
                message: message || "",
            });
            if (_history[symbol].length > getOpts().maxHistory) {
                _history[symbol].shift();
            }

            // Dispatch for visual update
            document.dispatchEvent(new CustomEvent("qa:whisper", {
                detail: { symbol: symbol, confidence: confidence, message: message },
            }));

            this._renderEnergyField(symbol, confidence);
        },

        _renderEnergyField: function (symbol, confidence) {
            var container = document.getElementById(getOpts().containerId);
            if (!container) return;

            // Remove old whisper overlay
            var old = container.querySelector(".qa-whisper-overlay");
            if (old) old.remove();

            var overlay = document.createElement("div");
            overlay.className = "qa-whisper-overlay";
            overlay.style.cssText =
                "position:absolute;pointer-events:none;inset:0;z-index:5;" +
                "transition:opacity " + getOpts().fadeDelayMs + "ms ease;" +
                "opacity:0;border-radius:inherit;";

            // Energy field: radial gradient based on confidence
            var intensity = Math.max(0.03, confidence * 0.15);
            var color = confidence >= 0.7 ? "rgba(25,135,84," : confidence >= 0.4 ? "rgba(255,193,7," : "rgba(220,53,69,";
            overlay.style.background =
                "radial-gradient(ellipse at 50% 80%, " + color + intensity + ") 0 0, " +
                "radial-gradient(ellipse at 20% 20%, " + color + (intensity * 0.5) + ") 0 0";

            container.appendChild(overlay);

            // Fade in, then out
            requestAnimationFrame(function () { overlay.style.opacity = "1"; });
            setTimeout(function () {
                overlay.style.opacity = "0";
                setTimeout(function () { if (overlay.parentNode) overlay.remove(); }, getOpts().fadeDelayMs);
            }, getOpts().fadeDelayMs);
        },

        getHistory: function (symbol) {
            return symbol ? (_history[symbol] || []) : _history;
        },

        clear: function (symbol) {
            if (symbol) {
                delete _history[symbol];
            } else {
                _history = {};
            }
        },
    };

    global.AlphaWhisper = AlphaWhisper;
})(window);
