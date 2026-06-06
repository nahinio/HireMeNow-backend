const Auth = {
  getToken() {
    return localStorage.getItem(CONFIG.TOKEN_KEY);
  },

  getUser() {
    return Utils.readJson(CONFIG.USER_KEY, null);
  },

  isLoggedIn() {
    return !!Auth.getToken();
  },

  setSession(token, user) {
    localStorage.setItem(CONFIG.TOKEN_KEY, token);
    Utils.writeJson(CONFIG.USER_KEY, user);
    App.updateNav();
  },

  clearSession() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
    App.updateNav();
  },

  async login(email, password, admin = false) {
    const path = admin ? '/auth/admin/login' : '/auth/login';
    const data = await Api.post(path, { email, password }, { auth: false });
    localStorage.setItem(CONFIG.TOKEN_KEY, data.access_token);
    const user = await Api.get('/auth/me');
    Auth.setSession(data.access_token, user);
    return user;
  },

  async register(payload) {
    const user = await Api.post('/auth/register', payload, { auth: false });
    const loginData = await Api.post('/auth/login', {
      email: payload.email,
      password: payload.password,
    }, { auth: false });
    Auth.setSession(loginData.access_token, user);
    return user;
  },

  logout() {
    Auth.clearSession();
    Router.navigate('/');
    Utils.showToast('Logged out', 'success');
  },

  requireRole(roles) {
    const user = Auth.getUser();
    if (!user || !Auth.getToken()) {
      Router.navigate('/login');
      return false;
    }
    if (!roles.includes(user.role)) {
      Utils.showToast('You do not have access to this page', 'error');
      Router.navigate('/');
      return false;
    }
    return true;
  },

  dashboardPath() {
    const user = Auth.getUser();
    if (!user) return '/login';
    if (user.role === 'admin') return '/admin';
    if (user.role === 'client') return '/client/dashboard';
    return '/freelancer/dashboard';
  },
};
