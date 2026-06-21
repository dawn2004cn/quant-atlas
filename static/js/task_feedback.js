(function (global) {
    'use strict';

    var _watchers = {};

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function renderProgress(el, data) {
        if (!el || !data) return;
        var steps = data.steps || [];
        var idx = data.step_index || 0;
        var percent = data.percent != null ? data.percent : 0;
        var stepHtml = steps.map(function (label, i) {
            var cls = i < idx ? 'qc-task-step done' : (i === idx ? 'qc-task-step active' : 'qc-task-step');
            return '<span class="' + cls + '">' + esc(label) + '</span>';
        }).join('');
        el.innerHTML =
            '<div class="qc-task-progress-bar"><div class="qc-task-progress-fill" style="width:' + percent + '%;"></div></div>' +
            '<div class="qc-task-progress-meta"><span>' + esc(data.message || data.state || '') + '</span>' +
            '<span class="qc-task-progress-pct">' + percent + '%</span></div>' +
            '<div class="qc-task-steps">' + stepHtml + '</div>';
    }

    function stop(taskId) {
        var w = _watchers[taskId];
        if (w && w.timer) clearInterval(w.timer);
        if (w && w.es) {
            try { w.es.close(); } catch (ignore) {}
        }
        delete _watchers[taskId];
    }

    async function poll(taskId, taskName, el, options) {
        var opts = options || {};
        var url = '/api/v1/system/tasks/' + encodeURIComponent(taskId) + '/feedback';
        if (taskName) url += '?task_name=' + encodeURIComponent(taskName);
        try {
            var res = await fetch(url, { credentials: 'include' });
            var json = await res.json();
            var data = json.data !== undefined ? json.data : json;
            renderProgress(el, data);
            if (typeof opts.onUpdate === 'function') opts.onUpdate(data);
            if (data.ready) {
                stop(taskId);
                if (typeof opts.onComplete === 'function') opts.onComplete(data);
            }
        } catch (e) {
            if (typeof opts.onError === 'function') opts.onError(e);
        }
    }

    function watchPoll(taskId, options) {
        var opts = options || {};
        if (!taskId) return;
        stop(taskId);
        var el = typeof opts.element === 'string' ? document.querySelector(opts.element) : opts.element;
        if (!el) return;
        poll(taskId, opts.taskName, el, opts);
        var timer = setInterval(function () {
            poll(taskId, opts.taskName, el, opts);
        }, opts.intervalMs || 2000);
        _watchers[taskId] = { timer: timer, el: el };
    }

    function watchStream(taskId, options) {
        var opts = options || {};
        if (!taskId || typeof EventSource === 'undefined' || opts.forcePoll) {
            watchPoll(taskId, options);
            return;
        }
        stop(taskId);
        var el = typeof opts.element === 'string' ? document.querySelector(opts.element) : opts.element;
        if (!el) return;

        var url = '/api/v1/system/tasks/' + encodeURIComponent(taskId) + '/stream';
        var qs = [];
        if (opts.taskName) qs.push('task_name=' + encodeURIComponent(opts.taskName));
        if (qs.length) url += '?' + qs.join('&');

        var es = new EventSource(url);
        _watchers[taskId] = { es: es, el: el };

        es.onmessage = function (ev) {
            try {
                var payload = JSON.parse(ev.data || '{}');
                var data = payload.feedback || payload;
                renderProgress(el, data);
                if (typeof opts.onUpdate === 'function') opts.onUpdate(data);
                if (data.ready || payload.done) {
                    stop(taskId);
                    if (typeof opts.onComplete === 'function') opts.onComplete(data);
                }
            } catch (e) {
                if (typeof opts.onError === 'function') opts.onError(e);
            }
        };

        es.onerror = function () {
            stop(taskId);
            watchPoll(taskId, options);
        };
    }

    global.QCTaskFeedback = {
        watch: watchStream,
        watchPoll: watchPoll,
        watchStream: watchStream,
        stop: stop,
        renderProgress: renderProgress,
    };
})(window);
