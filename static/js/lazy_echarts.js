/**
 * lazy_echarts.js — Load ECharts only when a chart page needs it.
 */
(function (global) {
    'use strict';

    var pending = null;

    function scriptSrc() {
        var tag = document.currentScript;
        if (tag && tag.getAttribute('data-echarts-src')) {
            return tag.getAttribute('data-echarts-src');
        }
        return '/static/js/vendor/echarts.min.js';
    }

    global.loadEcharts = function loadEcharts() {
        if (global.echarts) {
            return Promise.resolve(global.echarts);
        }
        if (pending) {
            return pending;
        }
        pending = new Promise(function (resolve, reject) {
            var el = document.createElement('script');
            el.src = scriptSrc();
            el.onload = function () {
                resolve(global.echarts);
            };
            el.onerror = function () {
                pending = null;
                reject(new Error('ECharts failed to load'));
            };
            document.head.appendChild(el);
        });
        return pending;
    };
}(window));
