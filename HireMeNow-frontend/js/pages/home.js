const Pages = {
  notFound() {
    return `${Components.pageHeader('Page not found')}
      <p>The page you requested does not exist.</p>
      <a class="btn" data-nav="/">Go home</a>`;
  },

  async home() {
    let jobs = [];
    let freelancers = [];
    try {
      const [j, f] = await Promise.all([
        Api.get('/jobs', { auth: false, query: { limit: 6 } }),
        Api.get('/freelancers', { auth: false, query: { limit: 6 } }),
      ]);
      jobs = j.items || [];
      freelancers = f.items || [];
      jobs.forEach((job) => Store.cacheSkills(job.required_skills || []));
    } catch { /* show empty sections */ }

    return `
      ${Components.pageHeader('HireMeNow', 'Connect skilled freelancers with great opportunities')}
      <section class="hero">
        <div class="hero-actions">
          <a class="btn btn-primary" data-nav="/jobs">Browse jobs</a>
          <a class="btn" data-nav="/freelancers">Find talent</a>
          <a class="btn" data-nav="/register">Get started</a>
        </div>
      </section>
      <section class="section">
        <h2>Latest jobs</h2>
        <div class="grid">${jobs.length ? jobs.map(Components.jobCard).join('') : Components.emptyState('No open jobs yet')}</div>
        <a class="link-more" data-nav="/jobs">View all jobs →</a>
      </section>
      <section class="section">
        <h2>Top freelancers</h2>
        <div class="grid">${freelancers.length ? freelancers.map(Components.freelancerCard).join('') : Components.emptyState('No freelancers yet')}</div>
        <a class="link-more" data-nav="/freelancers">Browse freelancers →</a>
      </section>`;
  },
};
