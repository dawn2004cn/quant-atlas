(function (global) {
  "use strict";

  function buildHref(ref) {
    if (!ref) return "#";
    if (ref.href) return ref.href;
    var sec = ref.section_id || "stockChart";
    if (ref.symbol) {
      var mkt = ref.market || "CN";
      return "/stock/" + encodeURIComponent(ref.symbol) + "?m=" + encodeURIComponent(mkt) + "#" + sec;
    }
    return "#" + sec;
  }

  function follow(ref) {
    if (!ref) return;
    var href = buildHref(ref);
    if (href.indexOf("#") === 0 && href.length > 1) {
      var id = href.slice(1);
      var el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        el.classList.add("qc-trace-highlight");
        setTimeout(function () { el.classList.remove("qc-trace-highlight"); }, 1800);
      }
      return;
    }
    if (href && href !== "#") {
      global.location.href = href;
    }
  }

  function renderButton(ref, label) {
    label = label || "追踪";
    if (!ref) return "";
    var href = buildHref(ref);
    return (
      '<a class="btn-soft btn-sm qc-trace-link" href="' + href + '" data-trace="1">' +
      label + "</a>"
    );
  }

  function renderEvidenceList(items, emptyText) {
    emptyText = emptyText || "暂无";
    if (!items || !items.length) {
      return "<li class=\"text-muted\">" + emptyText + "</li>";
    }
    return items.map(function (x) {
      var trace = x.trace_ref ? " " + renderButton(x.trace_ref) : "";
      return "<li>" + (x.text || "") + trace + "</li>";
    }).join("");
  }

  global.QCTraceLink = {
    buildHref: buildHref,
    follow: follow,
    renderButton: renderButton,
    renderEvidenceList: renderEvidenceList,
  };

  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var link = t.closest("a.qc-trace-link[data-trace]");
    if (!link) return;
    var href = link.getAttribute("href") || "";
    if (href.indexOf("#") === 0) {
      ev.preventDefault();
      follow({ section_id: href.slice(1) });
    }
  });
})(window);
