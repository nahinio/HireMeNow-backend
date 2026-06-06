const Router = {
  routes: {},

  register(path, handler) {
    Router.routes[path] = handler;
  },

  getPath() {
    const hash = location.hash.slice(1) || '/';
    const qIdx = hash.indexOf('?');
    return qIdx === -1 ? hash : hash.slice(0, qIdx);
  },

  navigate(path) {
    location.hash = path.startsWith('#') ? path.slice(1) : path;
  },

  async render() {
    const path = Router.getPath();
    const main = document.getElementById('main');
    if (!main) return;

    main.innerHTML = '<div class="loading">Loading…</div>';

    const handler = Router.match(path);
    if (!handler) {
      main.innerHTML = Pages.notFound();
      return;
    }

    try {
      const html = await handler();
      main.innerHTML = html;
      Router.bindEvents(main);
    } catch (err) {
      main.innerHTML = `<div class="alert alert-error">${Utils.escapeHtml(Utils.parseApiError(err))}</div>`;
    }
  },

  match(path) {
    if (Router.routes[path]) return Router.routes[path];
    for (const [pattern, handler] of Object.entries(Router.routes)) {
      if (!pattern.includes(':')) continue;
      const regex = new RegExp('^' + pattern.replace(/:[^/]+/g, '([^/]+)') + '$');
      if (regex.test(path)) {
        return async () => {
          const m = path.match(regex);
          const params = {};
          const keys = (pattern.match(/:[^/]+/g) || []).map((k) => k.slice(1));
          keys.forEach((k, i) => { params[k] = m[i + 1]; });
          return handler(params);
        };
      }
    }
    return null;
  },

  bindEvents(root) {
    root.querySelectorAll('[data-nav]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        Router.navigate(el.getAttribute('data-nav'));
      });
    });

    root.querySelectorAll('form[data-form]').forEach((form) => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = form.getAttribute('data-form');
        const handler = FormHandlers[name];
        if (handler) await handler(form);
      });
    });
  },
};

const FormHandlers = {};
