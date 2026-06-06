const Api = {
  async request(method, path, { body, auth = true, formData = false, query } = {}) {
    const url = new URL(CONFIG.API_URL + path);
    if (query) {
      Object.entries(query).forEach(([k, v]) => {
        if (v !== '' && v != null) url.searchParams.set(k, v);
      });
    }

    /** @type {RequestInit} */
    const opts = { method, headers: {} };

    if (auth) {
      const token = Auth.getToken();
      if (token) opts.headers['Authorization'] = `Bearer ${token}`;
    }

    if (formData) {
      opts.body = body;
    } else if (body != null) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }

    let res;
    try {
      res = await fetch(url.toString(), opts);
    } catch {
      throw { detail: 'Network error — check connection or CORS settings on the backend' };
    }

    if (res.status === 204) return null;

    const contentType = res.headers.get('content-type') || '';
    const data = contentType.includes('json') ? await res.json() : await res.text();

    if (!res.ok) throw data;
    return data;
  },

  get(path, opts) {
    return Api.request('GET', path, opts);
  },
  post(path, body, opts = {}) {
    return Api.request('POST', path, { body, ...opts });
  },
  patch(path, body, opts = {}) {
    return Api.request('PATCH', path, { body, ...opts });
  },
  delete(path, opts = {}) {
    return Api.request('DELETE', path, opts);
  },
  upload(path, file, opts = {}) {
    const fd = new FormData();
    fd.append('file', file);
    return Api.request('POST', path, { body: fd, formData: true, ...opts });
  },
};
