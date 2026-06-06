const Store = {
  getConversations() {
    return Utils.readJson(CONFIG.CONVERSATIONS_KEY, []);
  },

  saveConversation(conv, meta = {}) {
    const list = Store.getConversations();
    const idx = list.findIndex((c) => c.id === conv.id);
    const entry = {
      id: conv.id,
      client_id: conv.client_id,
      freelancer_id: conv.freelancer_id,
      job_id: conv.job_id,
      phase: conv.phase,
      created_at: conv.created_at,
      ...meta,
    };
    if (idx >= 0) list[idx] = { ...list[idx], ...entry };
    else list.unshift(entry);
    Utils.writeJson(CONFIG.CONVERSATIONS_KEY, list);
  },

  removeConversation(id) {
    Utils.writeJson(
      CONFIG.CONVERSATIONS_KEY,
      Store.getConversations().filter((c) => c.id !== id)
    );
  },

  cacheSkills(skills) {
    const existing = Utils.readJson(CONFIG.SKILLS_CACHE_KEY, []);
    const map = new Map(existing.map((s) => [s.id, s]));
    skills.forEach((s) => {
      if (s && s.id) map.set(s.id, s);
    });
    Utils.writeJson(CONFIG.SKILLS_CACHE_KEY, [...map.values()]);
  },

  getCachedSkills() {
    return Utils.readJson(CONFIG.SKILLS_CACHE_KEY, []);
  },

  async refreshSkillsCache() {
    const skills = new Map();
    try {
      const data = await Api.get('/skills', { auth: false, query: { limit: 100 } });
      (data.items || []).forEach((s) => {
        skills.set(s.id, {
          id: s.id,
          name: s.name,
          description: s.description || '',
          is_active: true,
          quiz: s.quiz || null,
        });
      });
    } catch { /* ignore */ }

    try {
      const courses = await Api.get('/courses', { auth: false, query: { limit: 100 } });
      (courses.items || []).forEach((c) => {
        if (c.skill_id && !skills.has(c.skill_id)) {
          skills.set(c.skill_id, {
            id: c.skill_id,
            name: c.skill_name || 'Skill',
            description: '',
            is_active: true,
          });
        }
      });
    } catch { /* ignore */ }

    try {
      const jobs = await Api.get('/jobs', { auth: false, query: { limit: 100 } });
      (jobs.items || []).forEach((j) => {
        (j.required_skills || []).forEach((s) => {
          if (!skills.has(s.id)) skills.set(s.id, s);
        });
      });
    } catch { /* ignore */ }

    Store.cacheSkills([...skills.values()]);
    return Store.getCachedSkills();
  },
};
