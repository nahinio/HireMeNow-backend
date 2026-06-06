const Utils = {
  escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  },

  formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  },

  formatMoney(val, negotiable) {
    if (negotiable) return 'Negotiable';
    if (val == null || val === '') return '—';
    return `$${Number(val).toLocaleString()}`;
  },

  resolveMediaUrl(url) {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    if (url.startsWith('/')) return CONFIG.API_BASE + url;
    return CONFIG.API_BASE + '/' + url;
  },

  getQueryParams() {
    const out = {};
    const search = new URLSearchParams(location.search);
    for (const [k, v] of search) out[k] = v;

    const hash = location.hash.slice(1);
    const qIdx = hash.indexOf('?');
    if (qIdx !== -1) {
      const hashParams = new URLSearchParams(hash.slice(qIdx + 1));
      for (const [k, v] of hashParams) out[k] = v;
    }
    return out;
  },

  handleEmailResetLink() {
    const token = new URLSearchParams(location.search).get('token');
    if (!token) return false;
    const hashRoute = `#/reset-password?token=${encodeURIComponent(token)}`;
    if (location.hash !== hashRoute) {
      history.replaceState(null, '', location.pathname);
      location.hash = `/reset-password?token=${encodeURIComponent(token)}`;
    }
    return true;
  },

  buildHash(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return qs ? `#${path}?${qs}` : `#${path}`;
  },

  debounce(fn, ms = 300) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  },

  readJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  },

  writeJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  },

  stars(rating) {
    const n = Math.round(Number(rating) || 0);
    return '★'.repeat(n) + '☆'.repeat(5 - n);
  },

  statusBadge(status) {
    return `<span class="badge badge-${Utils.escapeHtml(status)}">${Utils.escapeHtml(status)}</span>`;
  },

  showToast(message, type = 'info') {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = message;
    el.className = `toast toast-${type} show`;
    clearTimeout(Utils._toastTimer);
    Utils._toastTimer = setTimeout(() => {
      el.classList.remove('show');
    }, 4000);
  },

  async copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      Utils.showToast('Copied to clipboard', 'success');
    } catch {
      Utils.showToast('Could not copy', 'error');
    }
  },

  formData(obj) {
    const fd = new FormData();
    Object.entries(obj).forEach(([k, v]) => {
      if (v != null) fd.append(k, v);
    });
    return fd;
  },

  parseApiError(err) {
    if (!err) return 'Something went wrong';
    if (typeof err === 'string') return err;
    if (err.detail) {
      if (typeof err.detail === 'string') return err.detail;
      if (typeof err.detail === 'object' && err.detail.missing_skills) {
        return `${err.detail.detail || 'Missing skills'}: ${err.detail.missing_skills.join(', ')}`;
      }
      if (Array.isArray(err.detail)) {
        return err.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
      }
    }
    if (err.title) return err.detail || err.title;
    return 'Request failed';
  },
};
