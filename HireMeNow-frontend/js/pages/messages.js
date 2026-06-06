const Messages = {
  pollTimer: null,

  stopPolling() {
    if (Messages.pollTimer) {
      clearInterval(Messages.pollTimer);
      Messages.pollTimer = null;
    }
  },
};

Object.assign(Pages, {
  async messagesList() {
    if (!Auth.requireRole(['freelancer', 'client'])) return '';
    Messages.stopPolling();
    const convos = Store.getConversations();

    const list = convos.length
      ? convos.map((c) => `
          <a class="card conversation-card" data-nav="/messages/${c.id}">
            <h3>${Utils.escapeHtml(c.job_title || 'Job conversation')}</h3>
            <p class="meta">Phase: ${Utils.escapeHtml(c.phase)} · Job ${Utils.escapeHtml(c.job_id?.slice(0, 8) || '')}…</p>
          </a>`).join('')
      : Components.emptyState('No conversations yet. They are created when a client selects you as an applicant.');

    return `
      ${Components.pageHeader('Messages')}
      <p class="hint">Conversations are stored locally. Clients get them automatically when selecting an applicant. Freelancers can paste a conversation ID shared by the client.</p>
      <form class="form card inline-form" id="add-conversation-form">
        ${Components.field('Conversation ID', 'conv_id', 'text', '', 'placeholder="UUID" required')}
        ${Components.field('Job title (optional)', 'job_title', 'text', '')}
        <button type="submit" class="btn btn-sm">Add conversation</button>
      </form>
      <div class="conversation-list">${list}</div>`;
  },

  async messagesChat({ id }) {
    if (!Auth.requireRole(['freelancer', 'client'])) return '';
    const convos = Store.getConversations();
    const meta = convos.find((c) => c.id === id) || { id };
    const user = Auth.getUser();

    let messages = [];
    try {
      messages = await Api.get(`/conversations/${id}/messages`);
    } catch (err) {
      return `${Components.pageHeader('Conversation')}
        <div class="alert alert-error">${Utils.escapeHtml(Utils.parseApiError(err))}</div>
        <a class="btn" data-nav="/messages">Back</a>`;
    }

    const renderMessages = (msgs) => msgs.map((m) => {
      const mine = m.sender_id === user.id;
      return `<div class="message ${mine ? 'mine' : 'theirs'}">
        <p>${Utils.escapeHtml(m.body)}</p>
        <small>${Utils.formatDate(m.sent_at)}${m.is_read ? ' · read' : ''}</small>
      </div>`;
    }).join('');

    Messages.stopPolling();
    Messages.pollTimer = setInterval(async () => {
      try {
        const msgs = await Api.get(`/conversations/${id}/messages`);
        const box = document.getElementById('message-list');
        if (box) box.innerHTML = renderMessages(msgs);
      } catch { /* ignore poll errors */ }
    }, CONFIG.MESSAGE_POLL_MS);

    const locked = meta.phase === 'is_locked';

    return `
      ${Components.pageHeader('Chat', meta.job_title || `Conversation ${id.slice(0, 8)}…`)}
      <a class="btn btn-sm" data-nav="/messages">← All messages</a>
      ${locked ? '<p class="alert">This conversation is locked.</p>' : ''}
      <div id="message-list" class="message-list">${renderMessages(messages)}</div>
      ${locked ? '' : `
        <form class="message-compose" data-form="sendMessage" data-conversation-id="${id}">
          ${Components.field('Message', 'body', 'textarea', '', 'required rows="2"')}
          <button type="submit" class="btn btn-primary">Send</button>
        </form>`}
      ${user.role === 'client' && meta.freelancer_id ? `
        <button class="btn btn-danger btn-sm" id="report-freelancer" data-user-id="${meta.freelancer_id}">Report freelancer</button>` : ''}
      ${user.role === 'freelancer' && meta.client_id ? `
        <button class="btn btn-danger btn-sm" id="report-client" data-user-id="${meta.client_id}">Report client</button>` : ''}`;
  },
});

FormHandlers.sendMessage = async (form) => {
  const id = form.dataset.conversationId;
  const fd = new FormData(form);
  try {
    await Api.post(`/conversations/${id}/messages`, { body: fd.get('body') });
    form.reset();
    const msgs = await Api.get(`/conversations/${id}/messages`);
    const user = Auth.getUser();
    const box = document.getElementById('message-list');
    if (box) {
      box.innerHTML = msgs.map((m) => {
        const mine = m.sender_id === user.id;
        return `<div class="message ${mine ? 'mine' : 'theirs'}">
          <p>${Utils.escapeHtml(m.body)}</p>
          <small>${Utils.formatDate(m.sent_at)}</small>
        </div>`;
      }).join('');
      box.scrollTop = box.scrollHeight;
    }
  } catch (err) {
    Utils.showToast(Utils.parseApiError(err), 'error');
  }
};

document.addEventListener('submit', (e) => {
  if (e.target.id === 'add-conversation-form') {
    e.preventDefault();
    const fd = new FormData(e.target);
    const id = fd.get('conv_id')?.trim();
    if (!id) return;
    Store.saveConversation({
      id,
      job_id: '',
      phase: 'active',
      client_id: '',
      freelancer_id: '',
      created_at: new Date().toISOString(),
    }, { job_title: fd.get('job_title') || 'Conversation' });
    Utils.showToast('Conversation added', 'success');
    Router.navigate(`/messages/${id}`);
  }
});

document.addEventListener('click', async (e) => {
  if (e.target.id === 'report-freelancer' || e.target.id === 'report-client') {
    const userId = e.target.dataset.userId;
    const description = prompt('Describe the issue:');
    if (!description?.trim()) return;
    try {
      await Api.post('/reports', { reported_user_id: userId, description });
      Utils.showToast('Report submitted', 'success');
    } catch (err) {
      Utils.showToast(Utils.parseApiError(err), 'error');
    }
  }
});

window.addEventListener('hashchange', () => {
  if (!Router.getPath().startsWith('/messages/')) Messages.stopPolling();
});
