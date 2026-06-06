const App = {
  init() {
    App.registerRoutes();
    App.bindGlobalNav();
    App.updateNav();
    window.addEventListener('hashchange', () => Router.render());

    if (Utils.handleEmailResetLink()) {
      Router.render();
    } else if (!location.hash) {
      location.hash = '#/';
    } else {
      Router.render();
    }

    Store.refreshSkillsCache();
  },

  bindGlobalNav() {
    document.querySelectorAll('.site-header [data-nav]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        Router.navigate(el.getAttribute('data-nav'));
      });
    });
  },

  registerRoutes() {
    Router.register('/', Pages.home);
    Router.register('/login', Pages.login);
    Router.register('/register', Pages.register);
    Router.register('/forgot-password', Pages.forgotPassword);
    Router.register('/reset-password', Pages.resetPassword);
    Router.register('/admin/login', Pages.adminLogin);

    Router.register('/jobs', Pages.jobs);
    Router.register('/jobs/:id', Pages.jobDetail);
    Router.register('/jobs/:id/review', Pages.jobReview);

    Router.register('/freelancers', Pages.freelancers);
    Router.register('/freelancers/:id', Pages.freelancerDetail);
    Router.register('/courses', Pages.courses);

    Router.register('/freelancer/dashboard', Pages.freelancerDashboard);
    Router.register('/freelancer/profile', Pages.freelancerProfile);
    Router.register('/freelancer/quizzes', Pages.freelancerQuizzes);
    Router.register('/freelancer/quizzes/:id', Pages.freelancerQuizTake);

    Router.register('/client/dashboard', Pages.clientDashboard);
    Router.register('/client/profile', Pages.clientProfile);
    Router.register('/client/jobs', Pages.clientJobs);
    Router.register('/client/jobs/new', Pages.clientJobNew);
    Router.register('/client/jobs/:id/applicants', Pages.clientApplicants);

    Router.register('/messages', Pages.messagesList);
    Router.register('/messages/:id', Pages.messagesChat);

    Router.register('/admin', Pages.adminDashboard);
    Router.register('/admin/skills', Pages.adminSkills);
    Router.register('/admin/courses', Pages.adminCourses);
    Router.register('/admin/reports', Pages.adminReports);
    Router.register('/admin/jobs', Pages.adminJobs);
    Router.register('/admin/jobs/:id/applicants', Pages.adminJobApplicants);
    Router.register('/admin/users', Pages.adminUsers);
  },

  updateNav() {
    const user = Auth.getUser();
    const authLinks = document.getElementById('nav-auth');
    const roleLinks = document.getElementById('nav-role');
    if (!authLinks || !roleLinks) return;

    if (user && Auth.getToken()) {
      authLinks.innerHTML = `
        <span class="nav-user">${Utils.escapeHtml(user.email)} (${user.role})</span>
        <button class="btn btn-sm" id="logout-btn">Logout</button>`;
      document.getElementById('logout-btn')?.addEventListener('click', Auth.logout);

      const dash = Auth.dashboardPath();
      roleLinks.innerHTML = `<a data-nav="${dash}">Dashboard</a>`;
      if (user.role === 'freelancer') {
        roleLinks.innerHTML += `<a data-nav="/freelancer/quizzes">Quizzes</a>`;
      }
      roleLinks.innerHTML += `<a data-nav="/messages">Messages</a>`;
      roleLinks.querySelectorAll('[data-nav]').forEach((el) => {
        el.addEventListener('click', (e) => {
          e.preventDefault();
          Router.navigate(el.getAttribute('data-nav'));
        });
      });
    } else {
      authLinks.innerHTML = `
        <a data-nav="/login">Login</a>
        <a class="btn btn-sm btn-primary" data-nav="/register">Sign up</a>`;
      roleLinks.innerHTML = '';
      authLinks.querySelectorAll('[data-nav]').forEach((el) => {
        el.addEventListener('click', (e) => {
          e.preventDefault();
          Router.navigate(el.getAttribute('data-nav'));
        });
      });
    }
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
