/**
 * scanner_events.js — SocketIO subscription for scanner anomaly events
 *
 * Listens on the existing QuantRealtime socket for market-room events
 * forwarded by the app->core event bus bridge.
 *
 * Events listened:
 *   'MarketDataUpdatedEvent' — forwarded when scanner detects anomaly
 */
(function (global) {
    'use strict';

    function init() {
        var rt = global.QuantRealtime;
        if (!rt || !rt.socket) {
            // Realtime socket not ready yet — retry when DOM settles
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 500); });
            }
            return;
        }

        var s = rt.socket;

        // Subscribe to market room for scanner events
        s.emit('subscribe', { room: 'market' });

        // Listen for scanner anomaly events forwarded by the bridge
        s.on('MarketDataUpdatedEvent', function (payload) {
            // payload: { symbol, market, reason, score, ... }
            document.dispatchEvent(new CustomEvent('quant:scanner-anomaly', {
                detail: payload
            }));
        });

        // Also forward to QCStateBus for reactive UI
        s.on('MarketDataUpdatedEvent', function (payload) {
            if (global.QCStateBus && payload.symbol) {
                var key = 'scanner.anomaly.' + payload.symbol;
                global.QCStateBus.publish(key, payload, { persist: false });
                // Also publish a general tick so watchers can batch
                global.QCStateBus.publish('scanner.last_anomaly', {
                    symbol: payload.symbol,
                    time: Date.now(),
                    reason: payload.reason || payload.alert_type || '异常',
                }, { persist: false });
            }
        });

        console.debug('[ScannerEvents] subscribed to market room');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window);
