Object.assign(Pages, {
  async jobs() {
    const params = Utils.getQueryParams();
    const page = Number(params.page) || 1;
    const q = params.q || '';
    const skill_id = params.skill_id || '';
    const skills = await Store.refreshSkillsCache();

    const skillOptions = skills.map(
      (s) => `<option value="${s.id}" ${s.id === skill_id ? 'selected' : ''}>${Utils.escapeHtml(s.name)}</option>`
    ).join('');

    const data = await Api.get('/jobs', {
      auth: false,
      query: { page, limit: 12, q: q || undefined, skill_id: skill_id || undefined },
    });
    (data.items || []).forEach((j) => Store.cacheSkills(j.required_skills || []));

    return `
      ${Components.pageHeader('Browse jobs')}
      <form class="filters card" id="job-filters">
        <input type="search" name="q" placeholder="Search title…" value="${Utils.escapeHtml(q)}">
        <select name="skill_id">
          <option value="">All skills</option>
          ${skillOptions}
        </select>
        <button type="submit" class="btn">Filter</button>
      </form>
      <div class="grid">${(data.items || []).length
        ? data.items.map(Components.jobCard).join('')
        : Components.emptyState('No jobs match your filters')}</div>
      ${Components.pagination(data.page, data.limit, data.total, '/jobs')}`;
  },

  async jobDetail({ id }) {
    const job = await Api.get(`/jobs/${id}`, { auth: Auth.isLoggedIn() });
    Store.cacheSkills(job.required_skills || []);

    const user = Auth.getUser();
    let actions = '';

    if (user?.role === 'freelancer' && job.status === 'open') {
      actions += `<button class="btn btn-primary" id="apply-job" data-job-id="${job.id}">Apply to this job</button>`;
    }
    if (user?.role === 'client' && user.id === job.client_id) {
      actions += `<a class="btn" data-nav="/client/jobs/${job.id}/applicants">View applicants</a>`;
    }
    if (user && (user.id === job.client_id || job.status !== 'open')) {
      if (['filled', 'pending_confirmation'].includes(job.status)) {
        actions += `<button class="btn" id="complete-job" data-job-id="${job.id}">Signal job complete</button>`;
      }
      if (job.status === 'pending_confirmation') {
        actions += `<a class="btn btn-primary" data-nav="/jobs/${job.id}/review">Submit review</a>`;
      }
      actions += `<a class="btn" data-nav="/messages?job_id=${job.id}">Messages</a>`;
    }

    const thumb = job.thumbnail_url
      ? `<img class="job-hero-img" src="${Utils.escapeHtml(Utils.resolveMediaUrl(job.thumbnail_url))}" alt="">`
      : '';

    const skills = (job.required_skills || [])
      .map((s) => `<span class="tag">${Utils.escapeHtml(s.name)}</span>`).join('');

    return `
      ${Components.pageHeader(job.title, job.company_name)}
      ${thumb}
      <div class="detail-meta">
        ${Utils.statusBadge(job.status)}
        <span>${Utils.formatMoney(job.salary_amount, job.salary_negotiable)}</span>
        <span>Posted ${Utils.formatDate(job.posted_at)}</span>
      </div>
      <div class="tags">${skills}</div>
      <div class="actions-bar">${actions}</div>
      <div class="detail-sections">
        <section><h3>About the role</h3><p>${Utils.escapeHtml(job.about_role || job.description)}</p></section>
        <section><h3>Responsibilities</h3><p>${Utils.escapeHtml(job.responsibilities)}</p></section>
        <section><h3>Requirements</h3>
          <p><strong>Education:</strong> ${Utils.escapeHtml(job.requirements_education)}</p>
          <p><strong>Experience:</strong> ${Utils.escapeHtml(job.requirements_experience)}</p>
          <p><strong>Additional:</strong> ${Utils.escapeHtml(job.requirements_additional)}</p>
        </section>
        ${job.other_benefits ? `<section><h3>Benefits</h3><p>${Utils.escapeHtml(job.other_benefits)}</p></section>` : ''}
        ${job.company_description ? `<section><h3>About company</h3><p>${Utils.escapeHtml(job.company_description)}</p></section>` : ''}
      </div>`;
  },

  async jobReview({ id }) {
    if (!Auth.requireRole(['freelancer', 'client'])) return '';
    const job = await Api.get(`/jobs/${id}`);

    return `
      ${Components.pageHeader('Submit review', job.title)}
      <form class="form card" data-form="submitReview" data-job-id="${id}">
        ${Components.field('Rating (1-5)', 'rating', 'number', '5', 'min="1" max="5" required')}
        ${Components.field('Review (min 20 characters)', 'body', 'textarea', '', 'minlength="20" required rows="5"')}
        <button type="submit" class="btn btn-primary">Submit review</button>
      </form>
      <p class="hint">Reviews publish when both parties submit. Job completes after both reviews.</p>`;
  },
});

document.addEventListener('click', async (e) => {
  if (e.target.id === 'apply-job') {
    const jobId = e.target.dataset.jobId;
    try {
      await Api.post(`/jobs/${jobId}/apply`);
      Utils.showToast('Application submitted!', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
  if (e.target.id === 'complete-job') {
    const jobId = e.target.dataset.jobId;
    try {
      await Api.post(`/jobs/${jobId}/complete`);
      Utils.showToast('Completion signalled', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});

document.addEventListener('submit', (e) => {
  if (e.target.id === 'job-filters') {
    e.preventDefault();
    const fd = new FormData(e.target);
    Router.navigate(Utils.buildHash('/jobs', {
      q: fd.get('q') || undefined,
      skill_id: fd.get('skill_id') || undefined,
    }).slice(1));
  }
});

FormHandlers.submitReview = async (form) => {
  const jobId = form.dataset.jobId;
  const fd = new FormData(form);
  try {
    await Api.post(`/jobs/${jobId}/review`, {
      rating: Number(fd.get('rating')),
      body: fd.get('body'),
    });
    Utils.showToast('Review submitted', 'success');
    Router.navigate(`/jobs/${jobId}`);
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};
