/**
 * qa-focus-bar.js — <qa-focus-bar> Web Component
 *
 * 渐进替换方案：不破坏现有 global_focus_bar.html，新页面可直接使用 <qa-focus-bar>。
 *
 * Slots:
 *   (default) — placeholder 文本，默认"代码/简称 600519"
 * Attributes:
 *   market  — 初始市场，默认 CN
 *   symbol  — 初始代码，默认空
 * Events:
 *   qa:focus-change — 输入后全组件冒泡，沿用 QAFocusContext 约定
 */
class QAFocusBar extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  static get observedAttributes() {
    return ['market', 'symbol'];
  }

  get market() { return this.getAttribute('market') || 'CN'; }
  set market(v) { this.setAttribute('market', v); }

  get symbol() { return this.getAttribute('symbol') || ''; }
  set symbol(v) { this.setAttribute('symbol', v); }

  attributeChangedCallback() {
    if (this.shadowRoot && this.shadowRoot.getElementById('fgSymbol')) {
      this.shadowRoot.getElementById('fgSymbol').value = this.symbol;
    }
    if (this.shadowRoot && this.shadowRoot.getElementById('fgMarket')) {
      this.shadowRoot.getElementById('fgMarket').value = this.market;
    }
  }

  connectedCallback() {
    this.render();
    this.syncFromHost();
    this.bind();
  }

  syncFromHost() {
    try {
      if (globalThis.QAFocusContext) {
        var f = globalThis.QAFocusContext.getFocus();
        if (f && f.symbol) {
          this.symbol = f.symbol;
          this.market = f.market;
          return;
        }
      }
    } catch (_) {}
    // fallback: use attributes
  }

  render() {
    var placeholder = (this.textContent || '').trim() || '代码/简称 600519';
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: inline-flex; align-items: center; gap: 8px; }
        .row { display: inline-flex; align-items: center; gap: 6px; }
        input, select {
          background: transparent;
          color: inherit;
          border: 1px solid rgba(255,255,255,.15);
          border-radius: 6px;
          padding: 4px 8px;
          font: inherit;
        }
        button {
          background: rgba(255,255,255,.08);
          color: inherit;
          border: 1px solid rgba(255,255,255,.15);
          border-radius: 6px;
          padding: 4px 10px;
          cursor: pointer;
        }
        button:hover { background: rgba(255,255,255,.14); }
        .links { margin-left: 8px; display: inline-flex; gap: 8px; }
        .links a { color: #9dc8ff; text-decoration: none; font-size: 12px; }
      </style>
      <span class="row">
        <input id="fgSymbol" value="${this._escapeAttr(this.symbol)}" placeholder="${this._escapeAttr(placeholder)}" autocomplete="off" />
        <select id="fgMarket">
          <option value="CN" ${this.market==='CN'?'selected':''}>A股</option>
          <option value="HK" ${this.market==='HK'?'selected':''}>港股</option>
          <option value="US" ${this.market==='US'?'selected':''}>美股</option>
          <option value="CRYPTO" ${this.market==='CRYPTO'?'selected':''}>Crypto</option>
        </select>
        <button id="fgApply" type="button">应用</button>
        <button id="fgClear" type="button">清</button>
      </span>
      <span class="links" id="fgLinks"></span>
    `;
  }

  bind() {
    var self = this;
    var root = this.shadowRoot;
    var symEl = root.getElementById('fgSymbol');
    var mktEl = root.getElementById('fgMarket');
    var applyBtn = root.getElementById('fgApply');
    var clearBtn = root.getElementById('fgClear');
    var linksEl = root.getElementById('fgLinks');

    function emit() {
      var detail = { symbol: symEl.value, market: mktEl.value };
      self.dispatchEvent(new CustomEvent('qa:focus-change', { detail, bubbles: true, composed: true }));
      // 兼容宿主页面已有的 QAFocusContext
      if (globalThis.QAFocusContext) {
        globalThis.QAFocusContext.setFocus(detail.symbol, detail.market, { silent: true });
      }
    }

    function refreshLinks() {
      if (!globalThis.QAFocusContext) return;
      try {
        var links = globalThis.QAFocusContext.buildShareLinks({ symbol: symEl.value, market: mktEl.value });
        linksEl.innerHTML = links.map(function (l) {
          return '<a href="' + self._escapeAttr(l.href) + '">' + self._escapeHtml(l.label) + '</a>';
        }).join('');
      } catch (_) {}
    }

    if (applyBtn) {
      applyBtn.addEventListener('click', function () { emit(); refreshLinks(); });
    }
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        symEl.value = '';
        emit();
      });
    }
    if (symEl) {
      symEl.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter') { ev.preventDefault(); emit(); refreshLinks(); }
      });
    }
  }

  _escapeAttr(v) { return String(v||'').replace(/[&<>"']/g, function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',\"'\":'&#39;'}[m];}); }
  _escapeHtml(v) { return String(v||'').replace(/[&<>"]/g, function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m];}); }
}

try {
  if (!globalThis.customElements.get('qa-focus-bar')) {
    globalThis.customElements.define('qa-focus-bar', QAFocusBar);
  }
} catch (_) {}
