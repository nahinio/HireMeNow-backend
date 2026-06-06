Object.assign(Pages, {
  login() {
    return `
      ${Components.pageHeader('Log in', 'Freelancers and clients')}
      <form class="form card" data-form="login">
        ${Components.field('Email', 'email', 'email', '', 'required autocomplete="email"')}
        ${Components.field('Password', 'password', 'password', '', 'required autocomplete="current-password"')}
        <button type="submit" class="btn btn-primary">Log in</button>
      </form>
      <p class="form-footer">
        <a data-nav="/forgot-password">Forgot password?</a> ·
        <a data-nav="/register">Create account</a> ·
        <a data-nav="/admin/login">Admin login</a>
      </p>`;
  },

  adminLogin() {
    return `
      ${Components.pageHeader('Admin login')}
      <form class="form card" data-form="adminLogin">
        ${Components.field('Email', 'email', 'email', '', 'required')}
        ${Components.field('Password', 'password', 'password', '', 'required')}
        <button type="submit" class="btn btn-primary">Log in as admin</button>
      </form>
      <p class="form-footer"><a data-nav="/login">Back to user login</a></p>`;
  },

  register() {
    return `
      ${Components.pageHeader('Create account')}
      <form class="form card" data-form="register">
        ${Components.field('Email', 'email', 'email', '', 'required autocomplete="email"')}
        ${Components.field('Password', 'password', 'password', '', 'required minlength="8" autocomplete="new-password"')}
        ${Components.field('Role', 'role', 'select', `
          <option value="freelancer">Freelancer (job seeker)</option>
          <option value="client">Client (employer)</option>`)}
        <div id="freelancer-fields">
          ${Components.field('Display name', 'display_name', 'text', '', 'required')}
        </div>
        <div id="client-fields" hidden>
          ${Components.field('Company name', 'company_name', 'text', '')}
        </div>
        <button type="submit" class="btn btn-primary">Register</button>
      </form>
      <p class="form-footer"><a data-nav="/login">Already have an account?</a></p>`;
  },

  forgotPassword() {
    return `
      ${Components.pageHeader('Forgot password')}
      <form class="form card" data-form="forgotPassword">
        ${Components.field('Email', 'email', 'email', '', 'required')}
        <button type="submit" class="btn btn-primary">Send reset link</button>
      </form>
      <div id="reset-token-area" hidden class="card alert">
        <p>Dev mode: reset token returned by API</p>
        <code id="reset-token-display"></code>
        <a class="btn btn-sm" id="use-reset-token">Use this token</a>
      </div>
      <p class="form-footer"><a data-nav="/login">Back to login</a></p>`;
  },

  resetPassword() {
    const { token } = Utils.getQueryParams();
    return `
      ${Components.pageHeader('Reset password')}
      <form class="form card" data-form="resetPassword">
        ${Components.field('Reset token', 'token', 'text', token || '', 'required')}
        ${Components.field('New password', 'new_password', 'password', '', 'required minlength="8"')}
        <button type="submit" class="btn btn-primary">Reset password</button>
      </form>`;
  },
});

FormHandlers.login = async (form) => {
  const fd = new FormData(form);
  try {
    await Auth.login(fd.get('email'), fd.get('password'));
    Utils.showToast('Welcome back!', 'success');
    Router.navigate(Auth.dashboardPath());
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.adminLogin = async (form) => {
  const fd = new FormData(form);
  try {
    await Auth.login(fd.get('email'), fd.get('password'), true);
    Utils.showToast('Admin logged in', 'success');
    Router.navigate('/admin');
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.register = async (form) => {
  const fd = new FormData(form);
  const payload = {
    email: fd.get('email'),
    password: fd.get('password'),
    role: fd.get('role'),
  };
  if (payload.role === 'freelancer') payload.display_name = fd.get('display_name');
  else payload.company_name = fd.get('company_name');

  try {
    await Auth.register(payload);
    Utils.showToast('Account created!', 'success');
    Router.navigate(Auth.dashboardPath());
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.forgotPassword = async (form) => {
  const fd = new FormData(form);
  try {
    const res = await Api.post('/auth/forgot-password', { email: fd.get('email') }, { auth: false });
    Utils.showToast(res.message || 'Check your email', 'success');
    if (res.reset_token) {
      const area = document.getElementById('reset-token-area');
      const display = document.getElementById('reset-token-display');
      if (area && display) {
        area.hidden = false;
        display.textContent = res.reset_token;
        document.getElementById('use-reset-token')?.addEventListener('click', () => {
          Router.navigate(`/reset-password?token=${encodeURIComponent(res.reset_token)}`);
        });
      }
    }
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.resetPassword = async (form) => {
  const fd = new FormData(form);
  try {
    await Api.post('/auth/reset-password', {
      token: fd.get('token'),
      new_password: fd.get('new_password'),
    }, { auth: false });
    Utils.showToast('Password reset successfully', 'success');
    Router.navigate('/login');
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

document.addEventListener('change', (e) => {
  if (e.target.name === 'role' && e.target.closest('form[data-form="register"]')) {
    const isFreelancer = e.target.value === 'freelancer';
    document.getElementById('freelancer-fields').hidden = !isFreelancer;
    document.getElementById('client-fields').hidden = isFreelancer;
  }
});
