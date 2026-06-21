/**
 * AI 研究报告页：六角色卡片、K 线嵌入、回测曲线、自选股与导出。
 * 依赖：全局 echarts、jQuery（由 base.html 提供）。
 */
(function (global) {
  "use strict";

  var LLM_STORAGE_KEY = "quant_atlas_ai_research_llm_v1";

  var AGENTS = [
    { key: "macro_analyst", title: "宏观分析", subtitle: "Macro Analyst" },
    { key: "fundamental_analyst", title: "基本面", subtitle: "Fundamental" },
    { key: "technical_analyst", title: "技术面", subtitle: "Technical" },
    { key: "sentiment_analyst", title: "情绪面", subtitle: "Sentiment" },
    { key: "backtest_optimizer", title: "回测优化", subtitle: "Backtest Optimizer" },
    { key: "risk_manager", title: "风险管理", subtitle: "Risk Manager" },
  ];

  /**
   * User-facing notification: prefer showToast, fall back to alert.
   */
  function notify(msg, type) {
    if (typeof window.showToast === 'function') {
      window.showToast(msg, type || 'info', 4000);
    } else {
      alert(msg);
    }
  }

  function parseTicker(ticker) {
    var t = String(ticker || "").trim().toUpperCase();
    if (!t) return { market: "CN", symbol: "" };
    if (t.endsWith(".SH") || t.endsWith(".SZ")) {
      return { market: "CN", symbol: t.replace(/\.(SH|SZ)$/i, "") };
    }
    if (t.endsWith(".HK")) return { market: "HK", symbol: t.replace(/\.HK$/i, "") };
    if (/^\d{6}$/.test(t)) return { market: "CN", symbol: t };
    if (t.indexOf(":") >= 0) {
      var p = t.split(":");
      return { market: (p[0] || "CN").toUpperCase(), symbol: p[1] || "" };
    }
    return { market: "CN", symbol: t };
  }

  function watchlistSymbol(ticker) {
    var ps = parseTicker(ticker);
    if (ps.market === "CN" && /^\d{6}$/.test(ps.symbol)) return ps.symbol;
    return ps.symbol || String(ticker || "").trim();
  }

  function isCnCivilTradingDay(dateStr) {
    var s = String(dateStr || "").slice(0, 10);
    var p = s.split("-").map(Number);
    if (p.length !== 3 || !p[0]) return false;
    var wd = new Date(p[0], p[1] - 1, p[2]).getDay();
    return wd !== 0 && wd !== 6;
  }

  function normalizeHistoryRow(item) {
    var date = String(item.date || item.Date || "").slice(0, 10);
    var open = Number(item.open ?? item.Open ?? NaN);
    var high = Number(item.high ?? item.High ?? NaN);
    var low = Number(item.low ?? item.Low ?? NaN);
    var close = Number(item.close ?? item.Close ?? NaN);
    var volume = Number(item.volume ?? item.Volume ?? 0);
    if (!date || !Number.isFinite(close)) return null;
    var o = Number.isFinite(open) ? open : close;
    var h = Number.isFinite(high) ? high : Math.max(o, close);
    var l = Number.isFinite(low) ? low : Math.min(o, close);
    return { date: date, open: o, high: Math.max(h, o, close), low: Math.min(l, o, close), close: close, volume: volume };
  }

  function calculateMA(prices, dayCount) {
    var result = [];
    for (var i = 0; i < prices.length; i++) {
      if (i < dayCount - 1) {
        result.push(null);
        continue;
      }
      var sum = 0;
      for (var j = 0; j < dayCount; j++) sum += prices[i - j];
      result.push(Number((sum / dayCount).toFixed(2)));
    }
    return result;
  }

  function renderKlineEmpty(dom, message) {
    if (!dom || !global.echarts) return;
    var existing = global.echarts.getInstanceByDom(dom);
    if (existing) existing.dispose();
    var chart = global.echarts.init(dom);
    chart.setOption({
      title: { text: message || "暂无K线", left: "center", top: "middle", textStyle: { fontSize: 14 } },
    });
  }

  /**
   * 与个股详情页一致的日 K + 成交量（简化 MA 条数以控制体积）。
   */
  function renderKlineCandle(dom, data) {
    if (!dom || !global.echarts) return;
    var existing = global.echarts.getInstanceByDom(dom);
    if (existing) existing.dispose();
    var chart = global.echarts.init(dom);
    if (!data || !data.dates || !data.closes || !data.dates.length) {
      renderKlineEmpty(dom, "暂无K线数据");
      return;
    }
    var dates = data.dates;
    var opens = data.opens || [];
    var highs = data.highs || [];
    var lows = data.lows || [];
    var closes = data.closes.map(function (v) {
      return Number(v);
    });
    var volumes = (data.volumes || []).map(function (v) {
      return Number(v) || 0;
    });
    var validRows = [];
    for (var i = 0; i < dates.length; i++) {
      var o = Number(opens[i]);
      var c = Number(closes[i]);
      var hi = Number(highs[i]);
      var lo = Number(lows[i]);
      if (!Number.isFinite(c) || c <= 0) continue;
      var o2 = Number.isFinite(o) && o > 0 ? o : c;
      if (!Number.isFinite(hi)) hi = Math.max(o2, c);
      if (!Number.isFinite(lo)) lo = Math.min(o2, c);
      var hi2 = Math.max(hi, o2, c);
      var lo2 = Math.min(lo, o2, c);
      if (!Number.isFinite(hi2) || !Number.isFinite(lo2) || hi2 < lo2) continue;
      validRows.push({
        date: dates[i],
        o: o2,
        c: c,
        lo: lo2,
        hi: hi2,
        vol: Number.isFinite(volumes[i]) && volumes[i] >= 0 ? volumes[i] : 0,
      });
    }
    if (!validRows.length) {
      renderKlineEmpty(dom, "暂无有效K线数据");
      return;
    }
    var vDates = validRows.map(function (r) {
      return r.date;
    });
    var vCloses = validRows.map(function (r) {
      return r.c;
    });
    var klineData = validRows.map(function (r) {
      return [r.o, r.c, r.lo, r.hi];
    });
    var ma5 = calculateMA(vCloses, 5);
    var ma30 = calculateMA(vCloses, 30);
    chart.setOption({
      title: { text: "日K线（研究标的）", left: "center" },
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { data: ["K线", "MA5", "MA30", "成交量"], top: 28 },
      grid: [
        { left: "3%", right: "4%", top: "14%", height: "58%" },
        { left: "3%", right: "4%", top: "78%", height: "16%" },
      ],
      xAxis: [
        { type: "category", data: vDates, boundaryGap: false, axisLine: { lineStyle: { color: "#8392A5" } } },
        {
          type: "category",
          data: vDates,
          boundaryGap: false,
          axisLine: { lineStyle: { color: "#8392A5" } },
          gridIndex: 1,
        },
      ],
      yAxis: [
        { type: "value", scale: true, axisLine: { lineStyle: { color: "#8392A5" } } },
        { type: "value", scale: true, axisLine: { lineStyle: { color: "#8392A5" } }, gridIndex: 1 },
      ],
      series: [
        {
          name: "K线",
          type: "candlestick",
          data: klineData,
          barMinWidth: 2,
          itemStyle: {
            color: "#118a55",
            color0: "#c23616",
            borderColor: "#118a55",
            borderColor0: "#c23616",
          },
        },
        { name: "MA5", type: "line", data: ma5, smooth: true, lineStyle: { width: 1, color: "#ff7f50" } },
        { name: "MA30", type: "line", data: ma30, smooth: true, lineStyle: { width: 1, color: "#da70d6" } },
        {
          name: "成交量",
          type: "bar",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: validRows.map(function (r) {
            return r.vol;
          }),
          itemStyle: {
            color: function (params) {
              var r = validRows[params.dataIndex];
              if (!r) return "#8392A5";
              return r.c >= r.o ? "#118a55" : "#c23616";
            },
          },
        },
      ],
    });
    global.addEventListener("resize", function onResize() {
      chart.resize();
    });
  }

  function loadKline(market, symbol, dom, onDone) {
    if (!symbol) {
      renderKlineEmpty(dom, "请先填写标的代码");
      if (onDone) onDone();
      return;
    }
    var end = new Date();
    var start = new Date();
    start.setDate(start.getDate() - 365);
    var startStr = start.toISOString().split("T")[0];
    var endStr = end.toISOString().split("T")[0];
    $.ajax({
      url: "/api/v1/stocks/" + market + "/" + encodeURIComponent(symbol) + "/history",
      method: "GET",
      data: { start: startStr, end: endStr },
      success: function (response) {
        if (response.status && response.status !== "success") {
          renderKlineEmpty(dom, "K线数据不可用");
          if (onDone) onDone();
          return;
        }
        var historyData = response.data || [];
        if (!Array.isArray(historyData) || !historyData.length) {
          renderKlineEmpty(dom, "暂无K线数据");
          if (onDone) onDone();
          return;
        }
        var rows = historyData.map(normalizeHistoryRow).filter(Boolean);
        if (market === "CN") rows = rows.filter(function (r) {
          return isCnCivilTradingDay(r.date);
        });
        rows.sort(function (a, b) {
          return a.date.localeCompare(b.date);
        });
        renderKlineCandle(dom, {
          dates: rows.map(function (r) {
            return r.date;
          }),
          opens: rows.map(function (r) {
            return r.open;
          }),
          highs: rows.map(function (r) {
            return r.high;
          }),
          lows: rows.map(function (r) {
            return r.low;
          }),
          closes: rows.map(function (r) {
            return r.close;
          }),
          volumes: rows.map(function (r) {
            return r.volume;
          }),
        });
        if (onDone) onDone();
      },
      error: function () {
        renderKlineEmpty(dom, "K线加载失败");
        if (onDone) onDone();
      },
    });
  }

  function renderBacktestEquityChart(dom, result) {
    if (!dom || !global.echarts) return;
    var existing = global.echarts.getInstanceByDom(dom);
    if (existing) existing.dispose();
    var chart = global.echarts.init(dom);
    var stockData = result.stock_data || {};
    var dates = stockData.dates || [];
    var closes = stockData.closes || [];
    var trades = result.trades || [];
    if (!dates.length) {
      chart.setOption({ title: { text: "暂无回测曲线数据", left: "center", top: "middle" } });
      return;
    }
    var buyPoints = [];
    var sellPoints = [];
    trades.forEach(function (trade) {
      var idx = dates.indexOf(trade.date);
      if (idx >= 0) {
        var point = [idx, trade.price];
        if (trade.action === "BUY") buyPoints.push(point);
        if (trade.action === "SELL") sellPoints.push(point);
      }
    });
    chart.setOption({
      title: { text: "默认参数回测：收盘价与买卖点（MA 策略）", left: "center" },
      tooltip: { trigger: "axis" },
      legend: { data: ["收盘价", "买入", "卖出"], top: 28 },
      grid: { left: 48, right: 24, top: 56, bottom: 36 },
      xAxis: { type: "category", data: dates, boundaryGap: false },
      yAxis: { type: "value", scale: true },
      series: [
        {
          name: "收盘价",
          type: "line",
          smooth: true,
          data: closes,
          lineStyle: { width: 3, color: "#103f91" },
          areaStyle: { color: "rgba(16,63,145,0.10)" },
        },
        { name: "买入", type: "scatter", data: buyPoints, symbolSize: 10, itemStyle: { color: "#c23616" } },
        { name: "卖出", type: "scatter", data: sellPoints, symbolSize: 10, itemStyle: { color: "#118a55" } },
      ],
    });
    global.addEventListener("resize", function () {
      chart.resize();
    });
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function renderMd(s) {
    return global.qcRenderMarkdown ? global.qcRenderMarkdown(s) : escapeHtml(s);
  }

function AiResearchReport(root) {
    this.root = root;
    this.userId = parseInt(root.getAttribute("data-user-id") || "0", 10);
    this.lastTicker = "";
    this.lastReport = null;
    this.shell();
}

AiResearchReport.prototype.shell = function () {
    var h =
      '<div class="aireport-toolbar">' +
      '  <div class="aireport-fields">' +
      '    <label class="aireport-label">标的代码</label>' +
      '    <input type="text" class="input-soft aireport-input" id="aireport-ticker" placeholder="如 600519 或 600519.SH" />' +
      '    <label class="aireport-label">研究问题</label>' +
      '    <textarea class="input-soft aireport-textarea" id="aireport-query" rows="2" placeholder="输入希望 AI 重点分析的方向"></textarea>' +
      '  </div>' +
      '  <div class="aireport-actions">' +
      '    <button type="button" class="btn-brand" id="aireport-run">生成研究报告</button>' +
      '    <button type="button" class="btn-soft" id="aireport-watchlist" disabled>一键加入自选股</button>' +
      '    <button type="button" class="btn-soft" id="aireport-brief-refresh" disabled>刷新决策简报</button>' +
      '    <button type="button" class="btn-soft" id="aireport-adopt" disabled>采纳到观察单</button>' +
      '    <button type="button" class="btn-soft" id="aireport-export" disabled>导出策略</button>' +
      "  </div>" +
      "</div>" +
      '<div id="aireport-error" class="aireport-error" style="display:none;"></div>' +
      '<div id="aireport-status" class="loading-state" style="display:none;"></div>' +
      '<div id="aireport-result" style="display:none;">' +
      '  <div class="section-shell" id="aireport-decision-panel" style="display:none;">' +
      '    <div class="panel-head">' +
      '      <div><h2 class="panel-title">决策简报</h2>' +
      '        <p class="panel-subtitle">与个股详情页同源：行情鲜度、归因摘要、板块上下文</p></div>' +
      '      <div style="display:flex;gap:8px;flex-wrap:wrap;">' +
      '        <a class="btn-soft btn-sm" id="aireport-brief-link" href="#" style="display:none;">完整简报</a>' +
      "      </div>" +
      "    </div>" +
      '    <div id="aireport-decision-freshness" class="qc-freshness-strip" style="display:none;margin-bottom:10px;"></div>' +
      '    <div id="aireport-decision-body"></div>' +
      "  </div>" +
      '  <div class="aireport-summary section-shell">' +
      '    <div class="panel-head"><h2 class="panel-title">综合摘要</h2>' +
      '      <span class="aireport-badge" id="aireport-confidence">置信度 —</span></div>' +
      '    <div class="aireport-summary-body" id="aireport-overall"></div>' +
      '    <div class="aireport-recs" id="aireport-recs"></div>' +
      "  </div>" +
      '  <div class="section-shell">' +
      '    <div class="panel-head"><h2 class="panel-title">K 线</h2><p class="panel-subtitle">与个股详情页相同数据源</p></div>' +
      '    <div class="aireport-kline-wrap"><div id="aireport-kline" class="aireport-kline"></div></div>' +
      "  </div>" +
      '  <div class="section-shell">' +
      '    <div class="panel-head"><h2 class="panel-title">回测结果图表</h2><p class="panel-subtitle">默认 MA 策略、近一年（与研究结论独立，供对照）</p></div>' +
      '    <div class="aireport-bt-wrap"><div id="aireport-bt-chart" class="aireport-bt-chart"></div></div>' +
      "  </div>" +
      '  <div class="aireport-agents" id="aireport-agents"></div>' +
      "</div>";
    this.root.innerHTML = h;
    var self = this;
    $("#aireport-run").on("click", function () {
      self.run();
    });
    $("#aireport-watchlist").on("click", function () {
      self.addWatchlist();
    });
    $("#aireport-export").on("click", function () {
      self.exportBundle();
    });
    $("#aireport-brief-refresh").on("click", function () {
      self.loadDecisionBriefPanel();
    });
    $("#aireport-adopt").on("click", function () {
      self.adoptFromBrief();
    });
  };

  AiResearchReport.prototype.bootstrapLlm = function () {
    var self = this;
    $.getJSON("/api/v1/llm/providers")
      .done(function (res) {
        if (!res || res.status !== "success" || !res.data) return;
        self._providers = res.data.providers || [];
        var $sel = $("#aireport-llm-provider");
        $sel.empty();
        self._providers.forEach(function (p) {
          $sel.append($("<option></option>").val(p.id).text(p.name));
        });
        self.restoreLlmLocal();
      })
      .fail(function () {
        $("#aireport-llm-provider").append($("<option></option>").val("").text("（加载提供方失败）"));
      });
    $("#aireport-llm-use-env").on("change", function () {
      $("#aireport-llm-custom").toggle(!$(this).is(":checked"));
    });
    $("#aireport-llm-provider").on("change", function () {
      self.applyProviderDefaults();
    });
    $("#aireport-llm-refresh").on("click", function () {
      self.refreshModels();
    });
    $("#aireport-llm-save-local").on("click", function () {
      self.saveLlmLocal();
    });
  };

  AiResearchReport.prototype.applyProviderDefaults = function () {
    var id = $("#aireport-llm-provider").val();
    var meta = null;
    for (var i = 0; i < (this._providers || []).length; i++) {
      if (this._providers[i].id === id) {
        meta = this._providers[i];
        break;
      }
    }
    if (meta && meta.default_base_url) {
      $("#aireport-llm-base").attr("placeholder", "默认：" + meta.default_base_url);
    } else {
      $("#aireport-llm-base").attr("placeholder", "留空则使用提供方默认网关");
    }
  };

  AiResearchReport.prototype.restoreLlmLocal = function () {
    try {
      var raw = localStorage.getItem(LLM_STORAGE_KEY);
      if (raw) {
        var o = JSON.parse(raw);
        $("#aireport-llm-use-env").prop("checked", !!o.use_env);
        $("#aireport-llm-custom").toggle(!$("#aireport-llm-use-env").is(":checked"));
        if (o.provider) $("#aireport-llm-provider").val(o.provider);
        if (o.base_url) $("#aireport-llm-base").val(o.base_url);
        if (o.api_key) $("#aireport-llm-key").val(o.api_key);
        this.applyProviderDefaults();
        if (o.model) {
          var $m = $("#aireport-llm-model");
          $m.append($("<option></option>").val(o.model).text(o.model));
          $m.val(o.model);
        }
        return;
      }
    } catch (e) {}
    $("#aireport-llm-use-env").prop("checked", false);
    $("#aireport-llm-custom").show();
    this.applyProviderDefaults();
  };

  AiResearchReport.prototype.saveLlmLocal = function () {
    var payload = {
      use_env: $("#aireport-llm-use-env").is(":checked"),
      provider: $("#aireport-llm-provider").val(),
      base_url: $("#aireport-llm-base").val().trim(),
      api_key: $("#aireport-llm-key").val(),
      model: $("#aireport-llm-model").val(),
    };
    try {
      localStorage.setItem(LLM_STORAGE_KEY, JSON.stringify(payload));
      notify("已保存到本机浏览器", "success");
    } catch (e) {
      notify("保存失败（可能为隐私模式）", "warning");
    }
  };

  AiResearchReport.prototype.setLlmModelsLoading = function (on) {
    var btn = $("#aireport-llm-refresh");
    if (on) {
      btn.prop("disabled", true).data("orig", btn.text()).text("拉取中…");
    } else {
      btn.prop("disabled", false).text(btn.data("orig") || "刷新模型列表");
    }
  };

  AiResearchReport.prototype.refreshModels = function () {
    var self = this;
    var provider = $("#aireport-llm-provider").val();
    var key = $("#aireport-llm-key").val().trim();
    var base = $("#aireport-llm-base").val().trim();
    if (!provider) {
      notify("请先选择提供方", "warning");
      return;
    }
    var meta = null;
    for (var i = 0; i < (this._providers || []).length; i++) {
      if (this._providers[i].id === provider) meta = this._providers[i];
    }
    if (meta && meta.needs_api_key && !key) {
      if (provider === "ollama") key = "ollama";
      else {
        notify("请填写 API Key 后再刷新", "warning");
        return;
      }
    }
    if (provider === "ollama" && !key) key = "ollama";
    this.setLlmModelsLoading(true);
    this.clearRunError();
    $.ajax({
      url: "/api/v1/llm/models",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ provider: provider, api_key: key, base_url: base || null }),
      success: function (res) {
        self.setLlmModelsLoading(false);
        if (!res || res.status !== "success" || !res.data || !Array.isArray(res.data.models)) {
          self.showRunError("刷新模型失败：响应格式异常");
          return;
        }
        var models = res.data.models;
        var $m = $("#aireport-llm-model");
        $m.empty();
        if (!models.length) {
          $m.append($("<option></option>").val("").text("（无可用模型）"));
        } else {
          models.forEach(function (id) {
            $m.append($("<option></option>").val(id).text(id));
          });
        }
      },
      error: function (xhr) {
        self.setLlmModelsLoading(false);
        var msg =
          (xhr.responseJSON && xhr.responseJSON.error && xhr.responseJSON.error.message) || xhr.statusText || "";
        self.showRunError("刷新模型列表失败：\n" + msg);
      },
    });
  };

  AiResearchReport.prototype.collectLlmPayload = function () {
    if ($("#aireport-llm-use-env").is(":checked")) return null;
    var provider = $("#aireport-llm-provider").val();
    var model = $("#aireport-llm-model").val();
    var key = $("#aireport-llm-key").val().trim();
    var base = $("#aireport-llm-base").val().trim();
    if (!provider) {
      notify("请选择 LLM 提供方，或勾选「使用服务器默认」", "warning");
      return false;
    }
    if (!model) {
      notify("请先「刷新模型列表」并选择模型，或勾选「使用服务器默认」", "warning");
      return false;
    }
    if (!key) {
      if (provider === "ollama") key = "ollama";
      else {
        notify("请填写 API Key，或勾选「使用服务器默认」", "warning");
        return false;
      }
    }
    return {
      provider: provider,
      api_key: key,
      model: model,
      base_url: base || null,
      temperature: 0.2,
    };
  };

  AiResearchReport.prototype.setBusy = function (msg) {
    var el = $("#aireport-status");
    if (msg) {
      el.show().text(msg);
    } else {
      el.hide().text("");
    }
  };

  AiResearchReport.prototype.clearRunError = function () {
    $("#aireport-error").hide().empty();
  };

  AiResearchReport.prototype.showRunError = function (text) {
    if (!text) {
      this.clearRunError();
      return;
    }
    $("#aireport-error")
      .show()
      .html('<pre class="aireport-error-pre">' + escapeHtml(text) + "</pre>");
  };

  AiResearchReport.prototype.run = function () {
    var ticker = $("#aireport-ticker").val().trim();
    var query = $("#aireport-query").val().trim();
    if (!ticker || !query) {
      notify("请填写标的代码与研究问题", "warning");
      return;
    }
    if (!this.userId || this.userId < 1) {
      notify("无法获取用户 ID，请重新登录", "error");
      return;
    }
    var self = this;
    this.clearRunError();
    this.setBusy("研究进行中，可能需要 1～3 分钟…");
    $("#aireport-result").hide();
    $("#aireport-watchlist, #aireport-export, #aireport-brief-refresh, #aireport-adopt").prop(
      "disabled",
      true
    );
    $("#aireport-decision-panel").hide();
    var body = { ticker: ticker, query: query, user_id: this.userId };
    $.ajax({
      url: "/api/v1/ai/research",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(body),
      success: function (res) {
        self.setBusy("");
        if (res.status && res.status !== "success") {
          self.showRunError((res.error && res.error.message) || "研究请求失败");
          return;
        }
        var data = res.data;
        if (!data) {
          self.showRunError("响应格式异常");
          return;
        }
        if (data.ok === false) {
          self.showRunError(data.message || data.error || "研究未完成");
          return;
        }
        self.clearRunError();
        self.lastTicker = ticker;
        self.lastReport = data;
        $("#aireport-result").show();
        self.renderSummary(data);
        self.renderAgentCards(data.agent_reports || {});
        var ps = parseTicker(ticker);
        loadKline(ps.market, ps.symbol, document.getElementById("aireport-kline"));
        self.loadDefaultBacktest(ps);
        $("#aireport-watchlist, #aireport-export, #aireport-brief-refresh, #aireport-adopt").prop(
          "disabled",
          false
        );
        self.loadDecisionBriefPanel(ps);
      },
      error: function (xhr) {
        self.setBusy("");
        var msg = (xhr.responseJSON && xhr.responseJSON.error && xhr.responseJSON.error.message) || xhr.statusText;
        self.showRunError("HTTP 请求失败：" + (msg || "未知错误"));
      },
    });
  };

  AiResearchReport.prototype.loadDecisionBriefPanel = function (parsed) {
    var ps = parsed || parseTicker(this.lastTicker || $("#aireport-ticker").val());
    if (!ps.symbol || !global.QAUserCenter) {
      $("#aireport-decision-panel").hide();
      return;
    }
    var self = this;
    var body = document.getElementById("aireport-decision-body");
    var fresh = document.getElementById("aireport-decision-freshness");
    var link = document.getElementById("aireport-brief-link");
    $("#aireport-decision-panel").show();
    if (body) body.innerHTML = '<div class="loading-state">正在加载决策简报…</div>';
    if (link) {
      link.href = global.QAUserCenter.stockDetailBriefHref(ps.symbol, ps.market);
      link.style.display = "inline-flex";
    }
    global.QAUserCenter.loadDecisionBrief(ps.symbol, ps.market, { timeline_limit: 20 })
      .then(function (brief) {
        self._lastBrief = brief;
        if (body) global.QAUserCenter.renderDecisionBriefMini(body, brief, fresh);
      })
      .catch(function (err) {
        if (body) {
          body.innerHTML =
            '<div class="text-muted">决策简报暂不可用：' + escapeHtml(err.message || String(err)) + "</div>";
        }
      });
  };

  AiResearchReport.prototype.adoptFromBrief = function () {
    var ps = parseTicker(this.lastTicker || $("#aireport-ticker").val());
    if (!ps.symbol) {
      notify("请先生成研究报告", "warning");
      return;
    }
    var adopt = global.QAUserCenter && global.QAUserCenter.adoptTradePlan;
    if (!adopt) {
      notify("采纳组件未加载", "warning");
      return;
    }
    var self = this;
    var header = (this._lastBrief && this._lastBrief.header) || {};
    adopt({
      symbol: ps.symbol,
      market: ps.market,
      name: header.name || ps.symbol,
      source: "ai_research_report",
      notes: ($("#aireport-query").val() || "").trim().slice(0, 200),
    })
      .then(function () {
        notify("已采纳到观察单", "success");
      })
      .catch(function (err) {
        notify("采纳失败：" + (err.message || String(err)), "error");
      });
  };

  AiResearchReport.prototype.renderSummary = function (data) {
    $("#aireport-overall")
      .addClass("markdown-body")
      .html(renderMd(data.overall_summary || "—"));
    var conf = data.confidence_score;
    $("#aireport-confidence").text(
      typeof conf === "number" && !isNaN(conf) ? "置信度 " + (conf * 100).toFixed(0) + "%" : "置信度 —"
    );
    var recs = data.recommendations || [];
    var html = recs
      .map(function (r) {
        return '<span class="aireport-rec-pill">' + escapeHtml(r) + "</span>";
      })
      .join("");
    $("#aireport-recs").html(html || '<span class="text-muted">暂无建议</span>');
  };

  AiResearchReport.prototype.renderAgentCards = function (reports) {
    var cards = AGENTS.map(function (a) {
      var body = reports[a.key] || "（无输出）";
      return (
        '<article class="aireport-card metric-card">' +
        '<header class="aireport-card-head">' +
        "<div><div class=\"aireport-card-title\">" +
        escapeHtml(a.title) +
        '</div><div class="aireport-card-sub">' +
        escapeHtml(a.subtitle) +
        "</div></div></header>" +
        '<div class="aireport-card-body markdown-body">' +
        renderMd(body) +
        "</div></article>"
      );
    }).join("");
    $("#aireport-agents").html(
      '<div class="panel-head" style="margin-bottom:16px;"><h2 class="panel-title">六角色分析</h2></div><div class="aireport-grid">' +
        cards +
        "</div>"
    );
  };

  AiResearchReport.prototype.loadDefaultBacktest = function (ps) {
    var dom = document.getElementById("aireport-bt-chart");
    if (!ps.symbol || ps.market !== "CN") {
      renderBacktestEquityChart(dom, {});
      return;
    }
    var end = new Date();
    var start = new Date();
    start.setDate(start.getDate() - 365);
    var payload = {
      symbol: ps.symbol,
      strategy: "MA",
      start_date: start.toISOString().split("T")[0],
      end_date: end.toISOString().split("T")[0],
      initial_capital: 100000,
    };
    $.ajax({
      url: "/api/v1/backtest",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(payload),
      success: function (res) {
        var raw = (res && res.data) || res.backtest_result || res;
        renderBacktestEquityChart(dom, raw || {});
      },
      error: function () {
        renderBacktestEquityChart(dom, {});
      },
    });
  };

  AiResearchReport.prototype.addWatchlist = function () {
    var sym = watchlistSymbol(this.lastTicker);
    if (!sym) return;
    $.ajax({
      url: "/api/v1/watchlist",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ symbol: sym }),
      success: function () {
        notify("已加入自选股", "success");
      },
      error: function () {
        notify("加入自选股失败", "error");
      },
    });
  };

  AiResearchReport.prototype.exportBundle = function () {
    if (!this.lastReport) return;
    var blob = new Blob(
      [
        JSON.stringify(
          {
            ticker: this.lastTicker,
            exported_at: new Date().toISOString(),
            report: this.lastReport,
          },
          null,
          2
        ),
      ],
      { type: "application/json;charset=utf-8" }
    );
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "ai-research-" + (this.lastTicker || "export").replace(/[^\w.-]+/g, "_") + ".json";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  global.AiResearchReport = AiResearchReport;
})(window);
