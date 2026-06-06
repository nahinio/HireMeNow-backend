Object.assign(Pages, {
  async adminDashboard() {
    if (!Auth.requireRole(['admin'])) return '';
    const [reports, jobs] = await Promise.all([
      Api.get('/admin/reports', { query: { status: 'pending', limit: 5 } }).catch(() => ({ items: [] })),
      Api.get('/admin/jobs', { query: { limit: 5 } }).catch(() => ({ items: [] })),
    ]);

    return `
      ${Components.pageHeader('Admin dashboard')}
      <nav class="admin-nav card">
        <a data-nav="/admin/skills">Skills & quizzes</a>
        <a data-nav="/admin/courses">Courses</a>
        <a data-nav="/admin/reports">Reports (${reports.total || 0})</a>
        <a data-nav="/admin/jobs">All jobs</a>
        <a data-nav="/admin/users">Ban user</a>
      </nav>
      <section class="section">
        <h2>Pending reports</h2>
        ${(reports.items || []).length
          ? reports.items.map((r) => `
              <div class="card">
                <p>${Utils.escapeHtml(r.description)}</p>
                <small>Reported user: ${r.reported_user_id}</small>
                <a class="btn btn-sm" data-nav="/admin/reports">Review →</a>
              </div>`).join('')
          : Components.emptyState('No pending reports')}
      </section>
      <section class="section">
        <h2>Recent jobs</h2>
        ${(jobs.items || []).map((item) => Components.jobCard(item.job)).join('') || Components.emptyState('No jobs')}
      </section>`;
  },

  adminSkills() {
    if (!Auth.requireRole(['admin'])) return '';
    return `
      ${Components.pageHeader('Skills & quizzes')}
      <div class="admin-grid">
        <form class="form card" data-form="adminCreateSkill">
          <h3>Create skill</h3>
          ${Components.field('Name', 'name', 'text', '', 'required')}
          ${Components.field('Description', 'description', 'textarea', '', 'rows="2"')}
          <button type="submit" class="btn btn-primary">Create skill</button>
        </form>
        <form class="form card" data-form="adminCreateSkillQuiz">
          <h3>Create skill + quiz (bulk)</h3>
          ${Components.field('Skill name', 'name', 'text', '', 'required')}
          ${Components.field('Description', 'description', 'textarea', '', 'rows="2"')}
          ${Components.field('Pass threshold %', 'pass_threshold', 'number', '80', 'min="0" max="100"')}
          ${Components.field('Publish quiz', 'published', 'checkbox', false)}
          ${Components.field('Question 1', 'q1_body', 'text', '', 'required')}
          ${Components.field('Q1 option A (correct)', 'q1_a', 'text', '', 'required')}
          ${Components.field('Q1 option B', 'q1_b', 'text', '', 'required')}
          ${Components.field('Question 2', 'q2_body', 'text', '', 'required')}
          ${Components.field('Q2 option A', 'q2_a', 'text', '', 'required')}
          ${Components.field('Q2 option B (correct)', 'q2_b', 'text', '', 'required')}
          <button type="submit" class="btn btn-primary">Create with quiz</button>
        </form>
      </div>
      <a class="btn" data-nav="/admin">← Dashboard</a>`;
  },

  async adminCourses() {
    if (!Auth.requireRole(['admin'])) return '';
    const data = await Api.get('/admin/courses', { query: { limit: 50 } });
    const skills = Store.getCachedSkills();

    const skillOptions = skills.map(
      (s) => `<option value="${s.id}">${Utils.escapeHtml(s.name)}</option>`
    ).join('');

    const rows = (data.items || []).map((c) => `
      <tr>
        <td>${Utils.escapeHtml(c.name)}</td>
        <td>${Utils.escapeHtml(c.skill_name || c.skill_id)}</td>
        <td>${c.is_active ? 'Yes' : 'No'}</td>
        <td><a href="${Utils.escapeHtml(c.link)}" target="_blank">Link</a></td>
        <td>
          <button class="btn btn-sm toggle-course" data-id="${c.id}" data-active="${!c.is_active}">${c.is_active ? 'Deactivate' : 'Activate'}</button>
          <button class="btn btn-sm btn-danger delete-course" data-id="${c.id}">Delete</button>
        </td>
      </tr>`).join('');

    return `
      ${Components.pageHeader('Courses')}
      <form class="form card" data-form="adminCreateCourse">
        ${Components.field('Skill', 'skill_id', 'select', `<option value="">Select skill</option>${skillOptions}`, 'required')}
        ${Components.field('Course name', 'name', 'text', '', 'required')}
        ${Components.field('Link', 'link', 'url', '', 'required')}
        <input type="file" id="course-thumbnail" accept="image/*">
        <input type="hidden" name="thumbnail_url" id="course-thumbnail-url">
        <button type="submit" class="btn btn-primary">Add course</button>
      </form>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Name</th><th>Skill</th><th>Active</th><th>Link</th><th>Actions</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <a class="btn" data-nav="/admin">← Dashboard</a>`;
  },

  async adminReports() {
    if (!Auth.requireRole(['admin'])) return '';
    const data = await Api.get('/admin/reports', { query: { limit: 50 } });

    const rows = (data.items || []).map((r) => `
      <tr>
        <td>${Utils.escapeHtml(r.description.slice(0, 80))}…</td>
        <td>${Utils.statusBadge(r.status)}</td>
        <td>${Utils.formatDate(r.created_at)}</td>
        <td>
          ${r.status === 'pending' ? `
            <button class="btn btn-sm resolve-report" data-id="${r.id}" data-status="approved">Approve</button>
            <button class="btn btn-sm resolve-report" data-id="${r.id}" data-status="rejected">Reject</button>` : '—'}
        </td>
      </tr>`).join('');

    return `
      ${Components.pageHeader('User reports')}
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Description</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4">No reports</td></tr>'}</tbody>
        </table>
      </div>
      <a class="btn" data-nav="/admin">← Dashboard</a>`;
  },

  async adminJobs() {
    if (!Auth.requireRole(['admin'])) return '';
    const data = await Api.get('/admin/jobs', { query: { limit: 30 } });

    const rows = (data.items || []).map((item) => `
      <tr>
        <td>${Utils.escapeHtml(item.job.title)}</td>
        <td>${Utils.escapeHtml(item.job.company_name)}</td>
        <td>${Utils.statusBadge(item.job.status)}</td>
        <td>${item.application_count} (${item.pending_count} pending)</td>
        <td><a class="btn btn-sm" data-nav="/admin/jobs/${item.job.id}/applicants">Applicants</a></td>
      </tr>`).join('');

    return `
      ${Components.pageHeader('All jobs')}
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Title</th><th>Company</th><th>Status</th><th>Applications</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <a class="btn" data-nav="/admin">← Dashboard</a>`;
  },

  async adminJobApplicants({ id }) {
    if (!Auth.requireRole(['admin'])) return '';
    const data = await Api.get(`/admin/jobs/${id}/applicants`);
    const rows = (data.applicants?.items || []).map((a) => `
      <tr>
        <td>${Utils.escapeHtml(a.profile.display_name)}</td>
        <td>${a.composite_score}</td>
        <td>${Utils.statusBadge(a.status)}</td>
      </tr>`).join('');

    return `
      ${Components.pageHeader('Job applicants')}
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Name</th><th>Score</th><th>Status</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <a class="btn" data-nav="/admin/jobs">← Jobs</a>`;
  },

  adminUsers() {
    if (!Auth.requireRole(['admin'])) return '';
    return `
      ${Components.pageHeader('Ban user')}
      <form class="form card" data-form="adminBanUser">
        ${Components.field('User ID (UUID)', 'user_id', 'text', '', 'required')}
        ${Components.field('Ban reason', 'ban_reason', 'textarea', '', 'required rows="3"')}
        <button type="submit" class="btn btn-danger">Ban user</button>
      </form>
      <form class="form card" data-form="adminDeleteReview">
        <h3>Delete review</h3>
        ${Components.field('Review ID (UUID)', 'review_id', 'text', '', 'required')}
        <button type="submit" class="btn btn-danger">Delete review</button>
      </form>
      <a class="btn" data-nav="/admin">← Dashboard</a>`;
  },
});

FormHandlers.adminCreateSkill = async (form) => {
  const fd = new FormData(form);
  try {
    const skill = await Api.post('/admin/skills', {
      name: fd.get('name'),
      description: fd.get('description') || '',
    });
    Store.cacheSkills([skill]);
    Utils.showToast(`Skill "${skill.name}" created`, 'success');
    form.reset();
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.adminCreateSkillQuiz = async (form) => {
  const fd = new FormData(form);
  const payload = {
    name: fd.get('name'),
    description: fd.get('description') || '',
    pass_threshold: Number(fd.get('pass_threshold')) || 80,
    published: fd.get('published') === 'on',
    questions: [
      {
        body: fd.get('q1_body'),
        position: 1,
        options: [
          { body: fd.get('q1_a'), is_correct: true },
          { body: fd.get('q1_b'), is_correct: false },
        ],
      },
      {
        body: fd.get('q2_body'),
        position: 2,
        options: [
          { body: fd.get('q2_a'), is_correct: false },
          { body: fd.get('q2_b'), is_correct: true },
        ],
      },
    ],
  };
  try {
    const res = await Api.post('/admin/skills/with-quiz', payload);
    Store.cacheSkills([res.skill]);
    Utils.showToast('Skill + quiz created', 'success');
    form.reset();
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.adminCreateCourse = async (form) => {
  const fd = new FormData(form);
  try {
    await Api.post('/admin/courses', {
      skill_id: fd.get('skill_id'),
      name: fd.get('name'),
      link: fd.get('link'),
      thumbnail_url: fd.get('thumbnail_url') || null,
    });
    Utils.showToast('Course created', 'success');
    Router.render();
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.adminBanUser = async (form) => {
  const fd = new FormData(form);
  if (!confirm('Ban this user?')) return;
  try {
    const res = await Api.post(`/admin/users/${fd.get('user_id')}/ban`, {
      ban_reason: fd.get('ban_reason'),
    });
    Utils.showToast(`User banned (${res.role})`, 'success');
    form.reset();
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.adminDeleteReview = async (form) => {
  const fd = new FormData(form);
  if (!confirm('Delete this review?')) return;
  try {
    await Api.delete(`/admin/reviews/${fd.get('review_id')}`);
    Utils.showToast('Review deleted', 'success');
    form.reset();
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

document.addEventListener('click', async (e) => {
  if (e.target.classList.contains('resolve-report')) {
    const id = e.target.dataset.id;
    const status = e.target.dataset.status;
    const msg = status === 'approved' ? 'Approve report and delete reported user?' : 'Reject report?';
    if (!confirm(msg)) return;
    try {
      await Api.patch(`/admin/reports/${id}`, { status });
      Utils.showToast('Report resolved', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
  if (e.target.classList.contains('toggle-course')) {
    try {
      await Api.patch(`/admin/courses/${e.target.dataset.id}`, { is_active: e.target.dataset.active === 'true' });
      Utils.showToast('Course updated', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
  if (e.target.classList.contains('delete-course')) {
    if (!confirm('Delete course?')) return;
    try {
      await Api.delete(`/admin/courses/${e.target.dataset.id}`);
      Utils.showToast('Course deleted', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});

document.addEventListener('change', async (e) => {
  if (e.target.id === 'course-thumbnail' && e.target.files?.[0]) {
    try {
      const res = await Api.upload('/admin/courses/thumbnail', e.target.files[0]);
      document.getElementById('course-thumbnail-url').value = res.url;
      Utils.showToast('Thumbnail uploaded', 'success');
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});
