/**
 * qa-health-banner.js — <qa-health-banner> Web Component
 *
 * Polls /api/v1/system/health-banner and renders inline banner card.
 * Replaces old inline #qcGlobalHealthBanner pattern with encapsulated WC.
 *
 * Attributes:
 *   poll-ms  — poll interval (default 60000)
 * Events:
 *   qa:health-change  — { level, message, allow_live_trading }
 */
class QAHealthBanner extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._timer = null;
    this._level = 'ok';
  }

  static get observedAttributes() { return ['poll-ms']; }

  get pollMs() { return parseInt(this.getAttribute('poll-ms'), 10) || 60000; }

  connectedCallback() {
    this.render();
    this._poll();
    this._timer = setInterval(() => this._poll(), this.pollMs);
  }

  disconnectedCallback() {
    if (this._timer) { clearInterval(this._timer); this._timer = null; }
  }

  render() {
    this.shadowRoot.innerHTML = 
      <style>
        :host { display: block; }
        .banner {
          display: flex; align-items: center; gap: 12px;
          padding: 8px 16px; border-radius: var(--radius-md, 8px);
          font-size: 13px; line-height: 1.5;
          transition: background .3s, opacity .3s;
        }
        .banner--ok { display: none; }
        .banner--warning {
          background: rgba(255,193,7,.12); border: 1px solid rgba(255,193,7,.3); color: #b8860b;
        }
        .banner--critical {
          background: rgba(220,53,69,.12); border: 1px solid rgba(220,53,69,.3); color: #b02a37;
        }
        .dot {
          width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
        }
        .dot--ok { background: #198754; }
        .dot--warning { background: #ffc107; }
        .dot--critical { background: #dc3545; animation: pulse 1.2s infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
        .msg { flex: 1; }
        .action a { color: inherit; text-decoration: underline; font-weight: 600; white-space: nowrap; }
      </style>
      <div class="banner banner--ok" id="banner" role="alert">
        <span class="dot dot--ok" id="dot"></span>
        <span class="msg" id="msg"></span>
        <span class="action"><a href="/alert-center" id="actionLink">预警中心</a></span>
      </div>
    ;
  }

  async _poll() {
    try {
      const res = await fetch('/api/v1/system/health-banner');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const body = await res.json();
      const data = body.data || body;
      this._apply(data);
    } catch (_) {
      // keep last known state on network error
    }
  }

  _apply(data) {
    const level = data.level || 'ok';
    const banner = this.shadowRoot.getElementById('banner');
    const dot = this.shadowRoot.getElementById('dot');
    const msg = this.shadowRoot.getElementById('msg');
    if (!banner || !dot || !msg) return;

    banner.className = 'banner banner--' + level;
    dot.className = 'dot dot--' + level;
    msg.textContent = data.message || '';

    if (this._level !== level) {
      this._level = level;
      this.dispatchEvent(new CustomEvent('qa:health-change', {
        detail: { level, message: data.message, allow_live_trading: data.allow_live_trading },
        bubbles: true, composed: true,
      }));
    }
  }
}

try {
  if (!globalThis.customElements.get('qa-health-banner')) {
    globalThis.customElements.define('qa-health-banner', QAHealthBanner);
  }
} catch (_) {}
