/**
 * MailMind AI — Centralized REST API Service Client.
 * Connects React frontend components to the FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function request(endpoint, options = {}) {
  const token = localStorage.getItem('mailmind_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const url = `${API_BASE}${endpoint}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (res.status === 204) {
      return { success: true };
    }

    const data = await res.json();
    if (!res.ok) {
      const errorMsg = data?.message || data?.detail || `API Error (${res.status})`;
      const err = new Error(errorMsg);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    // Distinguish between network failures and HTTP error responses
    if (!error.status) {
      error.isNetworkError = true;
      error.message = 'Backend server unreachable. Make sure FastAPI is running on port 8000.';
    }
    throw error;
  }
}

export const api = {
  // ── Authentication & User ──
  auth: {
    getDemoToken: () => request('/auth/demo-token', { method: 'POST' }),
    getMe: () => request('/auth/me'),
    getGoogleStatus: () => request('/auth/google/status'),
    getGoogleAuthUrl: () => request('/auth/google/url'),
    disconnectGoogle: () => request('/auth/google/disconnect', { method: 'POST' }),
  },

  // ── Emails ──
  emails: {
    list: (params = {}) => {
      const q = new URLSearchParams();
      if (params.folder && params.folder !== 'all') q.set('folder', params.folder);
      if (params.category && params.category !== 'all') q.set('category', params.category);
      if (params.search) q.set('search', params.search);
      if (params.is_read !== undefined) q.set('is_read', params.is_read);
      if (params.is_starred !== undefined) q.set('is_starred', params.is_starred);
      if (params.skip !== undefined) q.set('skip', params.skip);
      if (params.limit !== undefined) q.set('limit', params.limit);
      const qs = q.toString() ? `?${q.toString()}` : '';
      return request(`/emails${qs}`);
    },
    get: (id) => request(`/emails/${id}`),
    stats: () => request('/emails/stats'),
    toggleStar: (id) => request(`/emails/${id}/star`, { method: 'PATCH' }),
    markRead: (id) => request(`/emails/${id}/read`, { method: 'PATCH' }),
    delete: (id) => request(`/emails/${id}`, { method: 'DELETE' }),
    send: (payload) => request('/emails/send', { method: 'POST', body: JSON.stringify(payload) }),
  },

  // ── AI Capabilities (Powered by Gemini) ──
  ai: {
    generateDraft: (payload) =>
      request('/ai/generate-draft', { method: 'POST', body: JSON.stringify(payload) }),
    approveDraft: (draftId, isApproved) =>
      request(`/ai/drafts/${draftId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ is_approved: isApproved }),
      }),
    summarize: (payload) =>
      request('/ai/summarize', { method: 'POST', body: JSON.stringify(payload) }),
    extractTasks: (payload) =>
      request('/ai/extract-tasks', { method: 'POST', body: JSON.stringify(payload) }),
    analyze: (payload) =>
      request('/ai/analyze', { method: 'POST', body: JSON.stringify(payload) }),
    rewrite: (payload) =>
      request('/ai/rewrite', { method: 'POST', body: JSON.stringify(payload) }),
    subject: (payload) =>
      request('/ai/subject', { method: 'POST', body: JSON.stringify(payload) }),
  },

  // ── Tasks ──
  tasks: {
    list: (includeCompleted = true) =>
      request(`/tasks?include_completed=${includeCompleted}`),
    create: (payload) =>
      request('/tasks', { method: 'POST', body: JSON.stringify(payload) }),
    toggle: (id) =>
      request(`/tasks/${id}/toggle`, { method: 'PATCH' }),
    delete: (id) =>
      request(`/tasks/${id}`, { method: 'DELETE' }),
  },

  // ── Calendar Events ──
  calendar: {
    list: () => request('/calendar/events'),
    create: (payload) =>
      request('/calendar/events', { method: 'POST', body: JSON.stringify(payload) }),
    delete: (id) =>
      request(`/calendar/events/${id}`, { method: 'DELETE' }),
  },

  // ── Notifications ──
  notifications: {
    list: (unreadOnly = false) =>
      request(`/notifications?unread_only=${unreadOnly}`),
    unreadCount: () => request('/notifications/unread-count'),
    markRead: (id) =>
      request(`/notifications/${id}/read`, { method: 'PATCH' }),
    markAllRead: () =>
      request('/notifications/mark-all-read', { method: 'POST' }),
  },

  // ── Preferences ──
  preferences: {
    get: () => request('/preferences'),
    update: (payload) =>
      request('/preferences', { method: 'PUT', body: JSON.stringify(payload) }),
  },

  // ── Health Check ──
  health: {
    check: () => request('/health'),
  },
};

export default api;
