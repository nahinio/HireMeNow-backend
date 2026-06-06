Object.assign(Pages, {
  async freelancerDashboard() {
    if (!Auth.requireRole(['freelancer'])) return '';
    const profile = await Api.get('/freelancer/profile');
    const jobs = await Api.get('/jobs', { query: { limit: 5 } }).catch(() => ({ items: [] }));
    const skills = await Api.get('/skills', { auth: false, query: { limit: 100 } }).catch(() => ({ items: [] }));
    const quizCount = (skills.items || []).filter((s) => s.quiz).length;
    const earnedSkills = (await Api.get(`/freelancers/${profile.id}`, { auth: false }).catch(() => ({ skills: [] }))).skills || [];

    return `
      ${Components.pageHeader(`Hello, ${profile.display_name}`, profile.availability_status)}
      <div class="dashboard-grid">
        <div class="card stat-card">
          <h3>Rating</h3>
          <p class="stat">${Utils.stars(profile.avg_rating)}</p>
          <small>${profile.review_count} reviews</small>
        </div>
        <div class="card stat-card">
          <h3>Skill badges</h3>
          <p class="stat">${earnedSkills.length}</p>
          <a data-nav="/freelancer/quizzes">Take quizzes →</a>
        </div>
        <div class="card stat-card">
          <h3>Available quizzes</h3>
          <p class="stat">${quizCount}</p>
        </div>
      </div>
      <div class="actions-bar">
        <a class="btn btn-primary" data-nav="/freelancer/profile">Edit profile</a>
        <a class="btn" data-nav="/jobs">Browse jobs</a>
        <a class="btn" data-nav="/messages">Messages</a>
      </div>
      <section class="section">
        <h2>Recommended open jobs</h2>
        <div class="grid">${(jobs.items || []).map(Components.jobCard).join('') || Components.emptyState('No jobs')}</div>
      </section>`;
  },

  async freelancerProfile() {
    if (!Auth.requireRole(['freelancer'])) return '';
    const p = await Api.get('/freelancer/profile');

    return `
      ${Components.pageHeader('My profile')}
      <form class="form card" data-form="freelancerProfile">
        ${Components.field('Display name', 'display_name', 'text', p.display_name)}
        ${Components.field('Bio', 'bio', 'textarea', p.bio, 'rows="4"')}
        ${Components.field('Contact email', 'contact_email', 'email', p.contact_email || '')}
        ${Components.field('LinkedIn URL', 'linkedin_url', 'url', p.linkedin_url || '')}
        ${Components.field('GitHub URL', 'github_url', 'url', p.github_url || '')}
        ${Components.field('Portfolio URL', 'portfolio_url', 'url', p.portfolio_url || '')}
        ${Components.field('Available for work', 'available_for_work', 'checkbox', p.availability_status === 'Available for Work')}
        <button type="submit" class="btn btn-primary">Save profile</button>
      </form>
      <div class="card">
        <h3>Profile picture</h3>
        ${p.profile_picture_url ? `<img class="preview-img" src="${Utils.escapeHtml(Utils.resolveMediaUrl(p.profile_picture_url))}" alt="">` : ''}
        <input type="file" id="profile-picture" accept="image/jpeg,image/png,image/webp">
        <button class="btn btn-sm" id="upload-picture">Upload picture</button>
      </div>
      <div class="card">
        <h3>Resume (PDF)</h3>
        ${p.resume_url ? `<a href="${Utils.escapeHtml(Utils.resolveMediaUrl(p.resume_url))}" target="_blank">View resume</a>` : '<p>No resume uploaded</p>'}
        <input type="file" id="profile-resume" accept="application/pdf">
        <button class="btn btn-sm" id="upload-resume">Upload resume</button>
      </div>
      <div class="card">
        <h3>Portfolio link</h3>
        <form data-form="addPortfolio">
          ${Components.field('Label', 'label', 'text', '', 'required')}
          ${Components.field('URL', 'url', 'url', '', 'required')}
          ${Components.field('Position', 'position', 'number', '1', 'min="1" required')}
          <button type="submit" class="btn btn-sm">Add link</button>
        </form>
      </div>
      <div class="card danger-zone">
        <h3>Delete account</h3>
        <button class="btn btn-danger" id="delete-freelancer-profile">Delete my profile</button>
      </div>`;
  },

  async freelancerQuizzes() {
    if (!Auth.requireRole(['freelancer'])) return '';
    const data = await Api.get('/skills', { auth: false, query: { limit: 100 } });
    const profile = await Api.get('/freelancer/profile');
    const publicProfile = await Api.get(`/freelancers/${profile.id}`, { auth: false }).catch(() => ({ skills: [] }));
    const earned = new Set((publicProfile.skills || []).map((s) => s.id));

    const quizzes = (data.items || []).filter((s) => s.quiz);
    const list = quizzes.length
      ? quizzes.map((s) => `
          <div class="card quiz-card">
            <h3>${Utils.escapeHtml(s.name)}</h3>
            <p>${s.quiz.question_count} questions · Pass: ${s.quiz.pass_threshold}%</p>
            ${earned.has(s.id) ? '<span class="badge badge-completed">Badge earned</span>' : ''}
            <a class="btn btn-sm" data-nav="/freelancer/quizzes/${s.quiz.quiz_id}">Take quiz</a>
          </div>`).join('')
      : Components.emptyState('No published quizzes yet. Admin must create and publish a skill quiz.');

    return `
      ${Components.pageHeader('Skill quizzes', 'Earn badges to apply for jobs')}
      <div class="grid">${list}</div>`;
  },

  async freelancerQuizTake({ id }) {
    if (!Auth.requireRole(['freelancer'])) return '';
    let quiz;
    try {
      quiz = await Api.get(`/quizzes/${id}`, { auth: false });
    } catch {
      return `${Components.pageHeader('Quiz not found')}
        <p>This quiz is unavailable or not published.</p>
        <a class="btn" data-nav="/freelancer/quizzes">Back</a>`;
    }

    const questions = [...(quiz.questions || [])].sort((a, b) => a.position - b.position);
    const questionHtml = questions.map((q, i) => {
      const options = (q.options || []).map(
        (o) => `<label class="radio"><input type="radio" name="q_${q.id}" value="${o.id}" required> ${Utils.escapeHtml(o.body)}</label>`
      ).join('');
      return `<div class="card quiz-question"><h4>Q${i + 1}. ${Utils.escapeHtml(q.body)}</h4>${options}</div>`;
    }).join('');

    return `
      ${Components.pageHeader(quiz.skill_name || 'Skill quiz')}
      <form id="quiz-attempt-form" data-quiz-id="${id}">
        ${questionHtml}
        <button type="submit" class="btn btn-primary">Submit answers</button>
      </form>
      <div id="quiz-result" hidden class="card"></div>`;
  },
});

FormHandlers.freelancerProfile = async (form) => {
  const fd = new FormData(form);
  const payload = {};
  ['display_name', 'bio', 'contact_email', 'linkedin_url', 'github_url', 'portfolio_url'].forEach((k) => {
    const v = fd.get(k);
    if (v !== '') payload[k] = v;
  });
  payload.available_for_work = fd.get('available_for_work') === 'on';
  try {
    await Api.patch('/freelancer/profile', payload);
    Utils.showToast('Profile updated', 'success');
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

FormHandlers.addPortfolio = async (form) => {
  const fd = new FormData(form);
  try {
    await Api.post('/freelancer/portfolio', {
      label: fd.get('label'),
      url: fd.get('url'),
      position: Number(fd.get('position')),
    });
    Utils.showToast('Portfolio link added', 'success');
    form.reset();
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

document.addEventListener('click', async (e) => {
  if (e.target.id === 'upload-picture') {
    const input = document.getElementById('profile-picture');
    if (!input?.files?.[0]) return Utils.showToast('Choose an image first', 'error');
    try {
      await Api.upload('/freelancer/profile/picture', input.files[0]);
      Utils.showToast('Picture uploaded', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
  if (e.target.id === 'upload-resume') {
    const input = document.getElementById('profile-resume');
    if (!input?.files?.[0]) return Utils.showToast('Choose a PDF first', 'error');
    try {
      await Api.upload('/freelancer/profile/resume', input.files[0]);
      Utils.showToast('Resume uploaded', 'success');
      Router.render();
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
  if (e.target.id === 'delete-freelancer-profile') {
    if (!confirm('Delete your account? This cannot be undone.')) return;
    try {
      await Api.delete('/freelancer/profile');
      Auth.clearSession();
      Utils.showToast('Account deleted', 'success');
      Router.navigate('/');
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});

document.addEventListener('submit', async (e) => {
  if (e.target.id !== 'quiz-attempt-form') return;
  e.preventDefault();
  const quizId = e.target.dataset.quizId;
  const payload = [...e.target.querySelectorAll('.quiz-question')].map((block) => {
    const input = block.querySelector('input[type="radio"]:checked');
    if (!input) return null;
    const questionId = input.name.replace(/^q_/, '');
    return { question_id: questionId, selected_option_id: input.value };
  }).filter(Boolean);

  try {
    const result = await Api.post(`/quizzes/${quizId}/attempt`, payload);
    const el = document.getElementById('quiz-result');
    if (el) {
      el.hidden = false;
      if (result.result === 'pass') {
        el.innerHTML = `<h3>Passed! Score: ${result.score}%</h3><p>Skill badge earned.</p>`;
        el.className = 'card alert-success';
      } else {
        const courses = (result.recommended_courses || []).map(
          (c) => `<li><a href="${Utils.escapeHtml(c.link)}" target="_blank">${Utils.escapeHtml(c.name)}</a></li>`
        ).join('');
        el.innerHTML = `<h3>Failed — Score: ${result.score}%</h3>
          <p>${(result.resources || []).join(' ')}</p>
          ${courses ? `<ul>${courses}</ul>` : ''}
          <button class="btn" onclick="location.reload()">Retry</button>`;
        el.className = 'card alert-error';
      }
    }
    e.target.hidden = true;
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
});
