Object.assign(Pages, {
  async freelancers() {
    const params = Utils.getQueryParams();
    const page = Number(params.page) || 1;
    const q = params.q || '';
    const available = params.available_for_work || '';
    const skills = await Store.refreshSkillsCache();

    const data = await Api.get('/freelancers', {
      auth: false,
      query: {
        page,
        limit: 12,
        q: q || undefined,
        available_for_work: available === 'true' ? true : available === 'false' ? false : undefined,
        skill_id: params.skill_id || undefined,
      },
    });

    const skillOptions = skills.map(
      (s) => `<option value="${s.id}">${Utils.escapeHtml(s.name)}</option>`
    ).join('');

    return `
      ${Components.pageHeader('Find freelancers')}
      <form class="filters card" id="freelancer-filters">
        <input type="search" name="q" placeholder="Search name…" value="${Utils.escapeHtml(q)}">
        <select name="skill_id"><option value="">All skills</option>${skillOptions}</select>
        <select name="available_for_work">
          <option value="">Any availability</option>
          <option value="true" ${available === 'true' ? 'selected' : ''}>Available</option>
          <option value="false" ${available === 'false' ? 'selected' : ''}>Not available</option>
        </select>
        <button type="submit" class="btn">Filter</button>
      </form>
      <div class="grid">${(data.items || []).length
        ? data.items.map(Components.freelancerCard).join('')
        : Components.emptyState('No freelancers found')}</div>
      ${Components.pagination(data.page, data.limit, data.total, '/freelancers')}`;
  },

  async freelancerDetail({ id }) {
    const f = await Api.get(`/freelancers/${id}`, { auth: false });
    const reviews = await Api.get(`/users/${f.user_id}/reviews`, { auth: false }).catch(() => []);

    const img = f.profile_picture_url
      ? `<img class="profile-hero" src="${Utils.escapeHtml(Utils.resolveMediaUrl(f.profile_picture_url))}" alt="">`
      : '';
    const skills = (f.skills || [])
      .map((s) => `<span class="tag">${Utils.escapeHtml(s.name)}</span>`).join('');
    const links = [
      f.linkedin_url && `<a href="${Utils.escapeHtml(f.linkedin_url)}" target="_blank">LinkedIn</a>`,
      f.github_url && `<a href="${Utils.escapeHtml(f.github_url)}" target="_blank">GitHub</a>`,
      f.portfolio_url && `<a href="${Utils.escapeHtml(f.portfolio_url)}" target="_blank">Portfolio</a>`,
    ].filter(Boolean).join(' · ');

    const reviewHtml = (reviews || []).length
      ? reviews.map((r) => `
          <div class="review-item">
            <p class="rating">${Utils.stars(r.rating)}</p>
            <p>${Utils.escapeHtml(r.body)}</p>
            <small>${Utils.formatDate(r.published_at || r.submitted_at)}</small>
          </div>`).join('')
      : Components.emptyState('No published reviews yet');

    let reportBtn = '';
    const user = Auth.getUser();
    if (user?.role === 'client') {
      reportBtn = `<button class="btn btn-danger btn-sm" id="report-user" data-user-id="${f.user_id}">Report user</button>`;
    }

    return `
      ${Components.pageHeader(f.display_name)}
      ${img}
      <p class="rating">${Utils.stars(f.avg_rating)} · ${f.review_count} reviews</p>
      <p>${Utils.escapeHtml(f.availability_status)}</p>
      <p>${Utils.escapeHtml(f.bio)}</p>
      <div class="tags">${skills}</div>
      <p class="links">${links}</p>
      ${reportBtn}
      <section class="section"><h2>Reviews</h2>${reviewHtml}</section>`;
  },

  async courses() {
    const params = Utils.getQueryParams();
    const page = Number(params.page) || 1;
    const data = await Api.get('/courses', { auth: false, query: { page, limit: 12, q: params.q || undefined } });
    (data.items || []).forEach((c) => {
      if (c.skill_id) Store.cacheSkills([{ id: c.skill_id, name: c.skill_name, description: '', is_active: true }]);
    });

    return `
      ${Components.pageHeader('Learning courses', 'Prepare for skill quizzes')}
      <form class="filters card" id="course-filters">
        <input type="search" name="q" placeholder="Search courses…" value="${Utils.escapeHtml(params.q || '')}">
        <button type="submit" class="btn">Search</button>
      </form>
      <div class="grid">${(data.items || []).length
        ? data.items.map(Components.courseCard).join('')
        : Components.emptyState('No courses available')}</div>
      ${Components.pagination(data.page, data.limit, data.total, '/courses')}`;
  },
});

document.addEventListener('submit', (e) => {
  if (e.target.id === 'freelancer-filters') {
    e.preventDefault();
    const fd = new FormData(e.target);
    Router.navigate(Utils.buildHash('/freelancers', {
      q: fd.get('q') || undefined,
      skill_id: fd.get('skill_id') || undefined,
      available_for_work: fd.get('available_for_work') || undefined,
    }).slice(1));
  }
  if (e.target.id === 'course-filters') {
    e.preventDefault();
    const fd = new FormData(e.target);
    Router.navigate(Utils.buildHash('/courses', { q: fd.get('q') || undefined }).slice(1));
  }
});

document.addEventListener('click', async (e) => {
  if (e.target.id === 'report-user') {
    const userId = e.target.dataset.userId;
    const description = prompt('Describe the issue (required):');
    if (!description?.trim()) return;
    try {
      await Api.post('/reports', { reported_user_id: userId, description });
      Utils.showToast('Report submitted', 'success');
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});
