const Components = {
  pageHeader(title, subtitle = '') {
    return `
      <header class="page-header">
        <h1>${Utils.escapeHtml(title)}</h1>
        ${subtitle ? `<p>${subtitle}</p>` : ''}
      </header>`;
  },

  pagination(page, limit, total, basePath) {
    const pages = Math.ceil(total / limit) || 1;
    if (pages <= 1) return '';
    let html = '<nav class="pagination">';
    for (let p = 1; p <= pages; p++) {
      html += `<a href="${Utils.buildHash(basePath, { page: p })}" class="page-link ${p === page ? 'active' : ''}">${p}</a>`;
    }
    html += '</nav>';
    return html;
  },

  jobCard(job) {
    const thumb = job.thumbnail_url
      ? `<img src="${Utils.escapeHtml(Utils.resolveMediaUrl(job.thumbnail_url))}" alt="" class="card-thumb">`
      : '<div class="card-thumb placeholder"></div>';
    const skills = (job.required_skills || [])
      .map((s) => `<span class="tag">${Utils.escapeHtml(s.name)}</span>`)
      .join('');
    return `
      <article class="card job-card">
        ${thumb}
        <div class="card-body">
          <h3><a data-nav="/jobs/${job.id}">${Utils.escapeHtml(job.title)}</a></h3>
          <p class="meta">${Utils.escapeHtml(job.company_name)} · ${Utils.formatMoney(job.salary_amount, job.salary_negotiable)}</p>
          <div class="tags">${skills}</div>
          ${Utils.statusBadge(job.status)}
          <a class="btn btn-sm" data-nav="/jobs/${job.id}">View details</a>
        </div>
      </article>`;
  },

  freelancerCard(f) {
    const img = f.profile_picture_url
      ? `<img src="${Utils.escapeHtml(Utils.resolveMediaUrl(f.profile_picture_url))}" alt="" class="avatar">`
      : '<div class="avatar placeholder"></div>';
    const skills = (f.skills || [])
      .map((s) => `<span class="tag">${Utils.escapeHtml(s.name)}</span>`)
      .join('');
    return `
      <article class="card freelancer-card">
        ${img}
        <div class="card-body">
          <h3><a data-nav="/freelancers/${f.profile_id}">${Utils.escapeHtml(f.display_name)}</a></h3>
          <p class="rating">${Utils.stars(f.avg_rating)} (${f.review_count})</p>
          <p class="meta">${Utils.escapeHtml(f.availability_status)}</p>
          <div class="tags">${skills}</div>
          <a class="btn btn-sm" data-nav="/freelancers/${f.profile_id}">View profile</a>
        </div>
      </article>`;
  },

  courseCard(c) {
    const thumb = c.thumbnail_url
      ? `<img src="${Utils.escapeHtml(Utils.resolveMediaUrl(c.thumbnail_url))}" alt="" class="card-thumb">`
      : '<div class="card-thumb placeholder"></div>';
    return `
      <article class="card course-card">
        ${thumb}
        <div class="card-body">
          <h3>${Utils.escapeHtml(c.name)}</h3>
          <p class="meta">Skill: ${Utils.escapeHtml(c.skill_name || '—')}</p>
          <a class="btn btn-sm" href="${Utils.escapeHtml(c.link)}" target="_blank" rel="noopener">Open course</a>
        </div>
      </article>`;
  },

  emptyState(msg) {
    return `<div class="empty-state">${Utils.escapeHtml(msg)}</div>`;
  },

  field(label, name, type = 'text', value = '', attrs = '') {
    const id = `field-${name}`;
    if (type === 'textarea') {
      return `
        <label for="${id}">${Utils.escapeHtml(label)}</label>
        <textarea id="${id}" name="${name}" ${attrs}>${Utils.escapeHtml(value)}</textarea>`;
    }
    if (type === 'select') {
      return `
        <label for="${id}">${Utils.escapeHtml(label)}</label>
        <select id="${id}" name="${name}" ${attrs}>${value}</select>`;
    }
    if (type === 'checkbox') {
      return `
        <label class="checkbox">
          <input type="checkbox" id="${id}" name="${name}" ${value ? 'checked' : ''} ${attrs}>
          ${Utils.escapeHtml(label)}
        </label>`;
    }
    return `
      <label for="${id}">${Utils.escapeHtml(label)}</label>
      <input type="${type}" id="${id}" name="${name}" value="${Utils.escapeHtml(value)}" ${attrs}>`;
  },
};
