Object.assign(Pages, {
  async clientDashboard() {
    if (!Auth.requireRole(['client'])) return '';
    const profile = await Api.get('/client/profile');
    const jobs = await Api.get('/jobs/mine', { query: { limit: 5 } }).catch(() => ({ items: [] }));

    return `
      ${Components.pageHeader(`Welcome, ${profile.company_name}`)}
      <div class="dashboard-grid">
        <div class="card stat-card">
          <h3>Company rating</h3>
          <p class="stat">${Utils.stars(profile.avg_rating)}</p>
          <small>${profile.review_count} reviews</small>
        </div>
        <div class="card stat-card">
          <h3>Your jobs</h3>
          <p class="stat">${jobs.total ?? jobs.items?.length ?? 0}</p>
        </div>
      </div>
      <div class="actions-bar">
        <a class="btn btn-primary" data-nav="/client/jobs/new">Post a job</a>
        <a class="btn" data-nav="/client/jobs">Manage jobs</a>
        <a class="btn" data-nav="/client/profile">Company profile</a>
        <a class="btn" data-nav="/messages">Messages</a>
      </div>
      <section class="section">
        <h2>Recent jobs</h2>
        <div class="grid">${(jobs.items || []).map(Components.jobCard).join('') || Components.emptyState('No jobs posted yet')}</div>
      </section>`;
  },

  async clientProfile() {
    if (!Auth.requireRole(['client'])) return '';
    const p = await Api.get('/client/profile');

    return `
      ${Components.pageHeader('Company profile')}
      <form class="form card" data-form="clientProfile">
        ${Components.field('Company name', 'company_name', 'text', p.company_name)}
        ${Components.field('Bio', 'bio', 'textarea', p.bio, 'rows="4"')}
        ${Components.field('Company website', 'company_link', 'url', p.company_link || '')}
        <button type="submit" class="btn btn-primary">Save</button>
      </form>
      <div class="card">
        <h3>Company logo</h3>
        ${p.profile_picture_url ? `<img class="preview-img" src="${Utils.escapeHtml(Utils.resolveMediaUrl(p.profile_picture_url))}" alt="">` : ''}
        <input type="file" id="client-picture" accept="image/jpeg,image/png,image/webp">
        <button class="btn btn-sm" id="upload-client-picture">Upload</button>
      </div>
      <div class="card danger-zone">
        <h3>Delete account</h3>
        <button class="btn btn-danger" id="delete-client-profile">Delete company account</button>
      </div>`;
  },

  async clientJobs() {
    if (!Auth.requireRole(['client'])) return '';
    const params = Utils.getQueryParams();
    const data = await Api.get('/jobs/mine', {
      query: { page: params.page || 1, limit: 12, status: params.status || undefined },
    });

    return `
      ${Components.pageHeader('My jobs')}
      <div class="actions-bar">
        <a class="btn btn-primary" data-nav="/client/jobs/new">Post new job</a>
      </div>
      <div class="grid">${(data.items || []).map((job) => {
        const extra = `<a class="btn btn-sm" data-nav="/client/jobs/${job.id}/applicants">Applicants</a>`;
        return Components.jobCard(job).replace('</article>', `${extra}</article>`);
      }).join('') || Components.emptyState('No jobs')}</div>
      ${Components.pagination(data.page, data.limit, data.total, '/client/jobs')}`;
  },

  async clientJobNew() {
    if (!Auth.requireRole(['client'])) return '';
    const skills = await Store.refreshSkillsCache();
    const profile = await Api.get('/client/profile');

    const skillCheckboxes = skills.length
      ? skills.map((s) => `
          <label class="checkbox">
            <input type="checkbox" name="skill_ids" value="${s.id}">
            ${Utils.escapeHtml(s.name)}
          </label>`).join('')
      : '<p class="hint">No skills cached yet. Admin must create skills first, or browse jobs/courses to populate.</p>';

    return `
      ${Components.pageHeader('Post a new job')}
      <form class="form card" data-form="createJob">
        ${Components.field('Job title', 'title', 'text', '', 'required')}
        ${Components.field('Company name', 'company_name', 'text', profile.company_name, 'required')}
        ${Components.field('About the role', 'about_role', 'textarea', '', 'required rows="3"')}
        ${Components.field('Responsibilities', 'responsibilities', 'textarea', '', 'required rows="3"')}
        ${Components.field('Salary amount', 'salary_amount', 'number', '', 'min="0"')}
        ${Components.field('Salary negotiable', 'salary_negotiable', 'checkbox', false)}
        ${Components.field('Requirements — education', 'requirements_education', 'textarea', '', 'rows="2"')}
        ${Components.field('Requirements — experience', 'requirements_experience', 'textarea', '', 'rows="2"')}
        ${Components.field('Requirements — additional', 'requirements_additional', 'textarea', '', 'rows="2"')}
        ${Components.field('Other benefits', 'other_benefits', 'textarea', '', 'rows="2"')}
        ${Components.field('Company description', 'company_description', 'textarea', '', 'rows="2"')}
        <fieldset><legend>Required skills (min 1)</legend>${skillCheckboxes}</fieldset>
        <div class="card">
          <h3>Job thumbnail</h3>
          <input type="file" id="job-thumbnail" accept="image/jpeg,image/png,image/webp">
          <input type="hidden" name="thumbnail_url" id="thumbnail-url">
          <p id="thumbnail-status" class="hint">Optional — upload before submitting</p>
        </div>
        <button type="submit" class="btn btn-primary">Publish job</button>
      </form>`;
  },

  async clientApplicants({ id }) {
    if (!Auth.requireRole(['client'])) return '';
    const job = await Api.get(`/jobs/${id}`);
    const data = await Api.get(`/jobs/${id}/applicants`);

    const rows = (data.items || []).map((a) => `
      <tr>
        <td>${Utils.escapeHtml(a.profile.display_name)}</td>
        <td>${Utils.escapeHtml(a.user.email)}</td>
        <td>${Utils.stars(a.profile.avg_rating)}</td>
        <td>${a.quiz_score_snapshot}%</td>
        <td>${a.composite_score}</td>
        <td>${Utils.statusBadge(a.status)}</td>
        <td>
          ${a.status === 'pending' && job.status === 'open'
            ? `<button class="btn btn-sm select-applicant" data-app-id="${a.application_id}" data-job-id="${id}">Select</button>`
            : '—'}
        </td>
      </tr>`).join('');

    return `
      ${Components.pageHeader('Applicants', job.title)}
      ${Utils.statusBadge(job.status)}
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Name</th><th>Email</th><th>Rating</th><th>Quiz</th><th>Score</th><th>Status</th><th>Action</th></tr>
          </thead>
          <tbody>${rows || '<tr><td colspan="7">No applicants yet</td></tr>'}</tbody>
        </table>
      </div>
      <a class="btn" data-nav="/client/jobs">Back to jobs</a>`;
  },
});

FormHandlers.clientProfile = async (form) => {
  const fd = new FormData(form);
  try {
    await Api.patch('/client/profile', {
      company_name: fd.get('company_name'),
      bio: fd.get('bio'),
      company_link: fd.get('company_link') || null,
    });
    Utils.showToast('Profile saved', 'success');
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.createJob = async (form) => {
  const fd = new FormData(form);
  const skillIds = [...form.querySelectorAll('input[name="skill_ids"]:checked')].map((el) => el.value);
  if (!skillIds.length) return Utils.showToast('Select at least one skill', 'error');

  const payload = {
    title: fd.get('title'),
    company_name: fd.get('company_name'),
    about_role: fd.get('about_role'),
    responsibilities: fd.get('responsibilities'),
    salary_negotiable: fd.get('salary_negotiable') === 'on',
    requirements_education: fd.get('requirements_education') || '',
    requirements_experience: fd.get('requirements_experience') || '',
    requirements_additional: fd.get('requirements_additional') || '',
    other_benefits: fd.get('other_benefits') || '',
    company_description: fd.get('company_description') || '',
    required_skill_ids: skillIds,
    thumbnail_url: fd.get('thumbnail_url') || null,
  };
  const salary = fd.get('salary_amount');
  if (salary) payload.salary_amount = Number(salary);

  try {
    const job = await Api.post('/jobs', payload);
    Utils.showToast('Job posted!', 'success');
    Router.navigate(`/jobs/${job.id}`);
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

document.addEventListener('change', async (e) => {
  if (e.target.id === 'job-thumbnail' && e.target.files?.[0]) {
    try {
      const res = await Api.upload('/jobs/thumbnail', e.target.files[0]);
      document.getElementById('thumbnail-url').value = res.url;
      document.getElementById('thumbnail-status').textContent = 'Thumbnail uploaded ✓';
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});

document.addEventListener('click', async (e) => {
  if (e.target.id === 'upload-client-picture') {
    const input = document.getElementById('client-picture');
    if (!input?.files?.[0]) return Utils.showToast('Choose an image', 'error');
    try {
      await Api.upload('/client/profile/picture', input.files[0]);
      Utils.showToast('Logo uploaded', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
  if (e.target.id === 'delete-client-profile') {
    if (!confirm('Delete your company account?')) return;
    try {
      await Api.delete('/client/profile');
      Auth.clearSession();
      Router.navigate('/');
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
  if (e.target.classList.contains('select-applicant')) {
    const applicationId = e.target.dataset.appId;
    const jobId = e.target.dataset.jobId;
    if (!confirm('Select this applicant? Others will be rejected.')) return;
    try {
      const res = await Api.post(`/jobs/${jobId}/select`, { application_id: applicationId });
      const job = await Api.get(`/jobs/${jobId}`);
      Store.saveConversation(res.conversation, {
        job_title: job.title || 'Selected job',
        freelancer_id: res.conversation.freelancer_id,
        client_id: res.conversation.client_id,
      });
      Utils.showToast('Applicant selected — share conversation ID with freelancer', 'success');
      alert(`Conversation ID (share with freelancer):\n\n${res.conversation.id}`);
      Router.navigate(`/messages/${res.conversation.id}`);
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});
