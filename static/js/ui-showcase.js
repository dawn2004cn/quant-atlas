/**
 * UI Design System showcase — module grid, filter, drawer (tmp/design parity).
 */
(function () {
    "use strict";

    var CATS = ["行情", "因子", "风控", "组合", "AI"];
    var NAMES = {
        行情: ["全球资产雷达", "盘口磁贴", "多源行情校验", "行业热力图", "波动率曲面", "新闻脉冲", "价量异动榜", "市场宽度仪表", "分钟级回放", "宏观日历"],
        因子: ["因子库总览", "IC 衰减曲线", "暴露矩阵", "因子组合器", "分层收益板", "相关性清洗", "Qlib 回测卡", "因子版本 diff", "风格漂移警报", "研究笔记"],
        风控: ["回撤防线", "净敞口控制", "止损队列", "VaR 压力测试", "流动性雷达", "异常数据源", "仓位红线", "黑名单复核", "合规审计轨迹", "风险日报"],
        组合: ["组合驾驶舱", "再平衡建议", "交易篮子", "持仓瀑布", "收益归因", "资金曲线", "费率估算", "多账户同步", "机构报告页", "策略容量"],
        AI: ["AI 投委会", "RD-Agent 任务", "研报摘要器", "信号旗扫描", "策略生成审阅", "提示词实验室", "多智能体辩论", "自然语言回测", "异常解释器", "投资经理 Copilot"],
    };
    var DETAIL = {
        行情: "连接多源行情、板块热度与实时预警，适合交易辅助后台和零售投资看板。",
        因子: "覆盖 Qlib 研究链路、因子有效性、暴露控制与实验记录。",
        风控: "强调红黄绿状态、人工复核、审计轨迹和组合下行保护。",
        组合: "支持机构组合管理、再平衡、归因、报告与多账户视图。",
        AI: "映射 RD-Agent、AI hedge fund、投委会和自然语言研究流。",
    };

    var modules = [];
    CATS.forEach(function (cat, ci) {
        NAMES[cat].forEach(function (title, i) {
            modules.push({
                id: String(ci * 10 + i + 1).padStart(2, "0"),
                cat: cat,
                title: title,
                desc: DETAIL[cat],
            });
        });
    });

    var currentFilter = "全部";
    var selected = modules[0];

    function qs(sel) {
        return document.querySelector(sel);
    }

    function qsa(sel) {
        return Array.prototype.slice.call(document.querySelectorAll(sel));
    }

    function accentColor(kind) {
        if (kind === "down") {
            return getComputedStyle(document.documentElement).getPropertyValue("--r").trim() || "#ff6b6b";
        }
        return getComputedStyle(document.documentElement).getPropertyValue("--a").trim() || "#55e48b";
    }

    function spark(color) {
        return (
            '<svg viewBox="0 0 120 34" aria-hidden="true">' +
            '<polyline fill="none" stroke="' + color + '" stroke-width="3" ' +
            'points="0,24 18,18 34,22 48,9 64,14 82,7 100,17 120,10"/></svg>'
        );
    }

    function renderAssets() {
        var el = qs("#qaAssets");
        if (!el) return;
        var rows = [
            ["SH000001", "上证指数", "+0.62%", "up"],
            ["HSI", "恒生科技", "-1.18%", "down"],
            ["CSI300", "沪深300", "+0.24%", "up"],
            ["USDCNH", "离岸人民币", "7.1821", "warn"],
        ];
        el.innerHTML = rows
            .map(function (a) {
                var cls = a[3] === "down" ? "qa-down" : a[3] === "warn" ? "qa-warn" : "qa-up";
                var stroke = a[3] === "down" ? accentColor("down") : accentColor("up");
                return (
                    '<div class="qa-asset">' +
                    "<div><b>" + a[0] + "</b><small>" + a[1] + "</small></div>" +
                    spark(stroke) +
                    '<b class="' + cls + '">' + a[2] + "</b></div>"
                );
            })
            .join("");
    }

    function renderGrid() {
        var searchEl = qs("#qaSearch");
        var q = searchEl ? searchEl.value.trim().toLowerCase() : "";
        var list = modules.filter(function (m) {
            var matchCat = currentFilter === "全部" || m.cat === currentFilter;
            var matchQ = !q || (m.title + m.cat + m.desc).toLowerCase().indexOf(q) >= 0;
            return matchCat && matchQ;
        });
        var grid = qs("#qaGrid");
        if (!grid) return;
        grid.innerHTML = list
            .map(function (m) {
                var dataSrc = m.cat === "AI" ? "RD-Agent" : "行情/任务";
                return (
                    '<article class="qa-card qa-module">' +
                    '<div class="qa-module-top">' +
                    '<span class="qa-module-id">QA-' + m.id + "</span>" +
                    '<span class="qa-tag">' + m.cat + "</span></div>" +
                    "<h3>" + m.title + "</h3>" +
                    "<p>" + m.desc + "</p>" +
                    '<div class="qa-mini">' +
                    "<span>数据: " + dataSrc + "</span>" +
                    "<span>状态: 可审计</span>" +
                    "<span>端: 桌面/平板/移动</span>" +
                    '<button type="button" class="qa-btn-ghost" data-module-id="' + m.id + '">查看详情</button>' +
                    "</div></article>"
                );
            })
            .join("");
        var countEl = qs("#qaResultCount");
        if (countEl) countEl.textContent = list.length + " / 50";
    }

    function setFilter(filter) {
        currentFilter = filter;
        qsa("[data-filter]").forEach(function (btn) {
            var on = btn.getAttribute("data-filter") === filter;
            btn.classList.toggle("active", on);
            btn.setAttribute("aria-pressed", on ? "true" : "false");
        });
        renderGrid();
    }

    function openModule(mod) {
        selected = mod;
        var title = qs("#qaDrawerTitle");
        var text = qs("#qaDrawerText");
        var spec = qs("#qaDrawerSpec");
        if (title) title.textContent = mod.title;
        if (text) text.textContent = mod.desc;
        if (spec) {
            spec.innerHTML = [
                ["场景", mod.cat],
                ["组件", "表格/状态/图表"],
                ["交互", "筛选/抽屉/复制"],
                ["响应", "桌面三栏/平板双栏/移动卡片"],
            ]
                .map(function (pair) {
                    return (
                        "<div><span>" + pair[0] + "</span><b>" + pair[1] + "</b></div>"
                    );
                })
                .join("");
        }
        var drawer = qs("#qaDrawer");
        if (drawer) drawer.classList.add("open");
    }

    function showToast() {
        var toast = qs("#qaToast");
        if (!toast) return;
        toast.classList.add("show");
        window.setTimeout(function () {
            toast.classList.remove("show");
        }, 1200);
    }

    function tickClock() {
        var el = qs("#qaLiveClock");
        if (!el) return;
        var now = new Date();
        var pad = function (n) {
            return String(n).padStart(2, "0");
        };
        el.textContent =
            "LIVE " + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
    }

    function init() {
        renderAssets();
        renderGrid();
        tickClock();
        window.setInterval(tickClock, 1000);

        document.addEventListener("click", function (e) {
            var filterBtn = e.target.closest("[data-filter]");
            if (filterBtn) {
                setFilter(filterBtn.getAttribute("data-filter"));
                return;
            }
            var actionBtn = e.target.closest("[data-filter-action]");
            if (actionBtn) {
                setFilter(actionBtn.getAttribute("data-filter-action"));
                return;
            }
            if (e.target.closest("[data-open-spec]")) {
                openModule(modules[0]);
                return;
            }
            var modBtn = e.target.closest("[data-module-id]");
            if (modBtn) {
                var id = modBtn.getAttribute("data-module-id");
                var mod = modules.find(function (m) {
                    return m.id === id;
                });
                if (mod) openModule(mod);
            }
        });

        var search = qs("#qaSearch");
        if (search) search.addEventListener("input", renderGrid);

        var density = qs("#qaDensity");
        if (density) {
            density.addEventListener("change", function (ev) {
                document.body.classList.toggle("qa-compact", ev.target.value === "compact");
            });
        }

        var closeBtn = qs("#qaDrawerClose");
        if (closeBtn) {
            closeBtn.addEventListener("click", function () {
                var drawer = qs("#qaDrawer");
                if (drawer) drawer.classList.remove("open");
            });
        }

        var exportBtn = qs("#qaExportBtn");
        if (exportBtn) {
            exportBtn.addEventListener("click", function () {
                var text = modules
                    .map(function (m) {
                        return m.id + " " + m.cat + " " + m.title;
                    })
                    .join("\n");
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(showToast);
                } else {
                    showToast();
                }
            });
        }

        var copyOne = qs("#qaCopyOne");
        if (copyOne) {
            copyOne.addEventListener("click", function () {
                var text = selected.title + "：" + selected.desc;
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(showToast);
                } else {
                    showToast();
                }
            });
        }

        var sideToggle = qs("#qaSideToggle");
        var sidePanel = qs("#qaSidePanel");
        if (sideToggle && sidePanel) {
            sideToggle.addEventListener("click", function () {
                sidePanel.classList.toggle("open");
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
