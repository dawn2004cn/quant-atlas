/**
 * qa-truth-badge.js — <qa-truth-badge> Web Component
 *
 * Displays Guardian verification badge above a chart/data card.
 *
 * Attributes:
 *   symbol  — stock symbol (required)
 *   market  — market (default CN)
 *
 * Usage:
 *   <qa-truth-badge symbol="600519" market="CN"></qa-truth-badge>
 */
class QATruthBadge extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._data = null;
    this._loading = false;
  }

  static get observedAttributes() { return ['symbol', 'market']; }

  get symbol() { return this.getAttribute('symbol') || ''; }
  set symbol(v) { this.setAttribute('symbol', v); }
  get market() { return this.getAttribute('market') || 'CN'; }

  attributeChangedCallback(name) {
    if ((name === 'symbol' || name === 'market') && this.symbol) {
      this._fetch();
    }
  }

  connectedCallback() {
    this.render();
    if (this.symbol) this._fetch();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: inline-flex; align-items: center; gap: 6px; }
        .badge {
          display: inline-flex; align-items: center; gap: 4px;
          padding: 2px 10px; border-radius: 999px;
          font-size: 11px; font-weight: 600;
          cursor: pointer; transition: all .2s;
          border: 1px solid transparent;
        }
        .badge--verified {
          background: rgba(25,135,84,.1); color: #198754; border-color: rgba(25,135,84,.25);
        }
        .badge--partial {
          background: rgba(255,193,7,.1); color: #b8860b; border-color: rgba(255,193,7,.25);
        }
        .badge--disputed, .badge--unverified {
          background: rgba(220,53,69,.1); color: #b02a37; border-color: rgba(220,53,69,.25);
        }
        .badge--loading { opacity: .5; pointer-events: none; }
        .icon { font-size: 13px; }
        .popup {
          display: none; position: absolute; z-index: 1000;
          background: var(--surface, #fff); color: var(--text, #13202d);
          border: 1px solid var(--surface-border, rgba(0,0,0,.12));
          border-radius: 8px; padding: 12px 16px; min-width: 280px;
          box-shadow: 0 4px 24px rgba(0,0,0,.12); font-size: 12px;
          line-height: 1.6;
        }
        .popup.show { display: block; }
        .popup h4 { margin: 0 0 8px; font-size: 13px; }
        .popup .row { display: flex; justify-content: space-between; padding: 2px 0; }
        .popup .src-ok { color: #198754; }
        .popup .src-outlier { color: #dc3545; }
        .popup .close { position: absolute; top: 6px; right: 10px; cursor: pointer; opacity: .5; }
      </style>
      <span class="badge badge--loading" id="badge" tabindex="0">
        <span class="icon">&#9898;</span>
        <span id="label">验证中...</span>
      </span>
      <div class="popup" id="popup"></div>
    `;
    var self = this;
    var badge = this.shadowRoot.getElementById('badge');
    var popup = this.shadowRoot.getElementById('popup');

    badge.addEventListener('click', function (e) {
      e.stopPropagation();
      var show = popup.classList.toggle('show');
      if (show && self._data) self._renderPopup();
    });

    // Close popup on outside click
    document.addEventListener('click', function (e) {
      if (!self.contains(e.target)) popup.classList.remove('show');
    });
  }

  async _fetch() {
    if (this._loading) return;
    this._loading = true;
    var badge = this.shadowRoot.getElementById('badge');
    if (badge) badge.className = 'badge badge--loading';
    var label = this.shadowRoot.getElementById('label');
    if (label) label.textContent = '验证中...';

    try {
      if (global.QCTruthBadge) {
        this._data = await global.QCTruthBadge.load(this.symbol, this.market);
        this._apply();
        this._loading = false;
        return;
      }
      var res = await fetch('/api/v1/truth/badge/' + encodeURIComponent(this.market) + '/' + encodeURIComponent(this.symbol));
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var body = await res.json();
      this._data = body.data || body;
      this._apply();
    } catch (_) {
      if (label) label.textContent = '数据源';
      if (badge) badge.className = 'badge badge--unverified';
    }
    this._loading = false;
  }

  _apply() {
    if (!this._data) return;
    var badge = this.shadowRoot.getElementById('badge');
    var label = this.shadowRoot.getElementById('label');
    if (!badge || !label) return;

    var level = this._data.trust_level || 'unverified';
    badge.className = 'badge badge--' + level;

    var icons = { verified: '\u2705', partial: '\u26A0\uFE0F', disputed: '\u274C', unverified: '\u2753' };
    var texts = { verified: 'Guardian \u8BA4\u8BC1', partial: '\u90E8\u5206\u5F02\u5E38', disputed: '\u6570\u636E\u4E89\u8BAE', unverified: '\u672A\u9A8C\u8BC1' };
    badge.querySelector('.icon').textContent = icons[level] || '\u2753';
    label.textContent = texts[level] || '\u672A\u77E5';
  }

  _renderPopup() {
    var popup = this.shadowRoot.getElementById('popup');
    if (!popup || !this._data) return;
    var d = this._data;
    var srcHtml = '';
    if (d.sources) {
      srcHtml = d.sources.map(function (s) {
        var cls = (d.outlier_sources || []).indexOf(s.source) >= 0 ? 'src-outlier' : 'src-ok';
        return '<div class="row ' + cls + '"><span>' + s.source + '</span><span>' + (s.value != null ? s.value.toFixed(2) : '--') + ' <small>(\u504F\u5DEE ' + s.diff_pct + '%)</small></span></div>';
      }).join('');
    }
    popup.innerHTML = '\n      <span class="close" data-truth-close>&times;</span>\n      <h4>' + d.symbol + ' \u6570\u636E\u771F\u76F8\u62A5\u544A</h4>\n      <div class="row"><span>\u4FE1\u4EFB\u5EA6</span><span>' + (d.confidence * 100).toFixed(0) + '%</span></div>\n      <hr style="margin:6px 0;opacity:.2">\n      <div><small>' + (d.evidence || '') + '</small></div>\n      <hr style="margin:6px 0;opacity:.2">\n      <div style="font-weight:600;margin-bottom:4px;">\u6570\u636E\u6E90</div>\n      ' + (srcHtml || '<div class="row"><span>\u65E0\u6570\u636E</span></div>') + '\n      <div style="margin-top:6px;font-size:11px;opacity:.6">\u5171\u8BC6\u503C: ' + (d.consensus_value != null ? d.consensus_value.toFixed(4) : '--') + '</div>\n    ';
    var closeBtn = popup.querySelector('[data-truth-close]');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () { popup.classList.remove('show'); });
    }
  }
}

try {
  if (!globalThis.customElements.get('qa-truth-badge')) {
    globalThis.customElements.define('qa-truth-badge', QATruthBadge);
  }
} catch (_) {}
