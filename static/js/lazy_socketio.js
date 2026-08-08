/**
 * lazy_socketio.js — Load Socket.IO client on demand (canvas / realtime pages).
 */
(function (global) {
    'use strict';

    var pending = null;

    function scriptSrc() {
        var tag = document.currentScript;
        if (tag && tag.getAttribute('data-socketio-src')) {
            return tag.getAttribute('data-socketio-src');
        }
        return '/static/js/vendor/socket.io.min.js';
    }

    global.loadSocketIo = function loadSocketIo() {
        if (typeof global.io === 'function') {
            return Promise.resolve(global.io);
        }
        if (pending) {
            return pending;
        }
        pending = new Promise(function (resolve, reject) {
            var el = document.createElement('script');
            el.src = scriptSrc();
            el.onload = function () {
                if (typeof global.io === 'function') {
                    resolve(global.io);
                } else {
                    pending = null;
                    reject(new Error('Socket.IO client unavailable'));
                }
            };
            el.onerror = function () {
                pending = null;
                reject(new Error('Socket.IO failed to load'));
            };
            document.head.appendChild(el);
        });
        return pending;
    };
}(window));
