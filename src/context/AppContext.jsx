import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { MOCK_EMAILS, MOCK_USER, MOCK_NOTIFICATIONS, FOLDER_COUNTS, MOCK_TASKS } from '../data/mockData';
import api from '../services/api';
import toast from 'react-hot-toast';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('mailmind_theme') || 'light';
  });
  const [currentPage, setCurrentPage] = useState('inbox'); // 'inbox' | 'analytics' | 'tasks' | 'calendar' | 'reports' | 'settings'
  const [user, setUser] = useState(MOCK_USER);
  const [emails, setEmails] = useState(MOCK_EMAILS);
  const [selectedEmail, setSelectedEmail] = useState(MOCK_EMAILS[0]);
  const [activeFolder, setActiveFolder] = useState('inbox');
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [composing, setComposing] = useState(false);
  const [replyTone, setReplyTone] = useState('professional');
  const [activePanel, setActivePanel] = useState('ai_reply');
  const [tasks, setTasks] = useState(MOCK_TASKS);
  const [folderCounts, setFolderCounts] = useState(FOLDER_COUNTS);
  const [preferences, setPreferences] = useState(null);
  const [integrationStatus, setIntegrationStatus] = useState({
    is_connected: false,
    is_demo_mode: true,
    is_oauth_configured: false,
    connected_email: null,
    account_status: 'disconnected',
    last_sync: null,
  });

  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [isMockData, setIsMockData] = useState(true);
  const [currentThread, setCurrentThread] = useState(null);
  const [loadingThread, setLoadingThread] = useState(false);

  // Sync theme with DOM and localStorage
  useEffect(() => {
    localStorage.setItem('mailmind_theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  // ── Load Real Data from Backend on Mount ──
  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      // 0. Ensure Demo Token if no token present in local storage
      if (!localStorage.getItem('mailmind_token')) {
        const tokenRes = await api.auth.getDemoToken().catch(() => null);
        if (tokenRes?.access_token) {
          localStorage.setItem('mailmind_token', tokenRes.access_token);
        }
      }

      // 1. Authenticate & Check Integration Status
      const [userRes, statusRes, prefRes] = await Promise.all([
        api.auth.getMe().catch(() => null),
        api.auth.getGoogleStatus().catch(() => null),
        api.preferences.get().catch(() => null),
      ]);

      const isGmailLive = Boolean(statusRes?.data?.is_connected);

      if (statusRes?.success && statusRes.data) {
        setIntegrationStatus(statusRes.data);
      }
      if (prefRes?.success && prefRes.data) {
        setPreferences(prefRes.data);
      }

      if (userRes?.success && userRes.data) {
        const connectedEmail = isGmailLive && statusRes?.data?.connected_email
          ? statusRes.data.connected_email
          : userRes.data.email;

        setUser({
          id: userRes.data.id,
          name: isGmailLive && statusRes?.data?.connected_email
            ? statusRes.data.connected_email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
            : userRes.data.name,
          email: connectedEmail,
          plan: userRes.data.plan || 'Pro Plan',
        });
        setIsMockData(!isGmailLive && Boolean(userRes.demo_mode));
      }

      // 2. Fetch Emails & Folder Counts
      const emailRes = await api.emails.list().catch(() => null);
      if (emailRes?.success && emailRes.data) {
        const rawItems = emailRes.data.items || [];
        const mappedEmails = rawItems.map(e => ({
          id: e.id,
          messageId: e.message_id,
          threadId: e.thread_id,
          from: {
            name: e.from_name || e.from_email || 'Unknown',
            email: e.from_email,
            avatar: (e.from_name || e.from_email || 'U').slice(0, 2).toUpperCase(),
          },
          to: e.to,
          subject: e.subject || '(No Subject)',
          preview: e.preview || (e.body ? e.body.slice(0, 80) : ''),
          body: e.body || '',
          time: e.received_at
            ? new Date(e.received_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : 'Recent',
          date: e.received_at ? e.received_at.split('T')[0] : '',
          category: e.category || 'Work',
          isRead: e.is_read,
          isStarred: e.is_starred,
          isImportant: e.is_important,
          folder: e.folder || 'inbox',
          urgency: e.urgency || 'low',
          requiresReply: e.requires_reply,
          suggestedReply: e.ai_suggested_reply || null,
          hasAttachments: e.has_attachments || false,
          aiAnalysis: {
            confidence: e.ai_confidence || 90,
            category: e.category || 'Work',
            priority: e.urgency === 'urgent' ? 'High' : 'Normal',
            sentiment: 'Neutral',
            requiresReply: e.requires_reply,
            keyPoints: e.ai_summary || [],
            suspiciousFlag: false,
            extractedTasks: [],
            extractedDeadlines: [],
          },
        }));

        if (isGmailLive) {
          // When Gmail is connected, display real data strictly
          setEmails(mappedEmails);
          setSelectedEmail(mappedEmails.length > 0 ? mappedEmails[0] : null);
          setIsMockData(false);
        } else if (mappedEmails.length > 0) {
          setEmails(mappedEmails);
          setSelectedEmail(mappedEmails[0]);
        }

        if (emailRes.data.folder_counts) {
          setFolderCounts(emailRes.data.folder_counts);
        }
      }

      // 3. Fetch Tasks
      const tasksRes = await api.tasks.list().catch(() => null);
      if (tasksRes?.success && tasksRes.data) {
        setTasks(tasksRes.data);
      }

      // 4. Fetch Notifications
      const notifsRes = await api.notifications.list().catch(() => null);
      if (notifsRes?.success && notifsRes.data?.items) {
        setNotifications(
          notifsRes.data.items.map(n => ({
            id: n.id,
            title: n.title,
            body: n.body,
            type: n.type || 'ai_draft',
            read: n.is_read,
            time: n.created_at ? 'Recently' : 'Just now',
            emailId: n.email_id,
          }))
        );
      }

      setIsBackendConnected(true);
    } catch (err) {
      console.warn('Backend unavailable or network error, running in local fallback mode:', err);
      setIsBackendConnected(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Handle OAuth callback parameters on return to application
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthStatus = params.get('oauth');
    const returnedToken = params.get('token');
    if (oauthStatus === 'success') {
      if (returnedToken) {
        localStorage.setItem('mailmind_token', returnedToken);
      }
      toast.success('Gmail account connected successfully! Synced with Google.');
      setCurrentPage('settings');
      window.history.replaceState({}, document.title, window.location.pathname);
      loadInitialData();
    } else if (oauthStatus === 'error') {
      const errorMsg = params.get('message') || 'Failed to connect Google account.';
      toast.error(decodeURIComponent(errorMsg));
      setCurrentPage('settings');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [loadInitialData]);

  // ── Actions Connected to Backend ──
  const syncGmail = useCallback(async () => {
    setSyncing(true);
    const syncToast = toast.loading('Syncing with Gmail...');
    try {
      const res = await api.emails.sync(30);
      if (res?.success) {
        toast.success(res.data?.message || 'Inbox updated from Gmail', { id: syncToast });
        await loadInitialData();
      } else {
        toast.error(res?.message || 'Sync failed', { id: syncToast });
      }
    } catch (err) {
      toast.error(err.message || 'Sync error', { id: syncToast });
    } finally {
      setSyncing(false);
    }
  }, [loadInitialData]);

  const loadThread = useCallback(async (threadId) => {
    if (!threadId) {
      setCurrentThread(null);
      return;
    }
    setLoadingThread(true);
    try {
      const res = await api.emails.getThread(threadId);
      if (res?.success && res.data?.messages) {
        setCurrentThread(res.data.messages);
      } else {
        setCurrentThread(null);
      }
    } catch {
      setCurrentThread(null);
    } finally {
      setLoadingThread(false);
    }
  }, []);

  const selectEmailWithThread = useCallback((email) => {
    setSelectedEmail(email);
    if (email?.threadId) {
      loadThread(email.threadId);
    } else {
      setCurrentThread(null);
    }
  }, [loadThread]);

  const markAsRead = useCallback(async (emailId) => {
    setEmails(prev => prev.map(e => e.id === emailId ? { ...e, isRead: true } : e));
    try {
      await api.emails.markRead(emailId);
    } catch {
      // Optimistic update retained
    }
  }, []);

  const toggleStar = useCallback(async (emailId) => {
    setEmails(prev => prev.map(e => e.id === emailId ? { ...e, isStarred: !e.isStarred } : e));
    try {
      await api.emails.toggleStar(emailId);
    } catch {
      // Optimistic update retained
    }
  }, []);

  const deleteEmail = useCallback(async (emailId) => {
    setEmails(prev => prev.filter(e => e.id !== emailId));
    try {
      await api.emails.delete(emailId);
      toast.success('Email deleted');
    } catch {
      toast.error('Failed to delete email on server');
    }
  }, []);

  const dismissNotification = useCallback(async (notifId) => {
    setNotifications(prev => prev.map(n => n.id === notifId ? { ...n, read: true } : n));
    try {
      await api.notifications.markRead(notifId);
    } catch {
      // Local state updated
    }
  }, []);

  const markAllNotificationsRead = useCallback(async () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    try {
      await api.notifications.markAllRead();
      toast.success('All notifications marked as read');
    } catch {
      // Local state updated
    }
  }, []);

  const toggleTask = useCallback(async (id) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
    try {
      await api.tasks.toggle(id);
    } catch {
      // Local state updated
    }
  }, []);

  const addTask = useCallback(async (task) => {
    try {
      const res = await api.tasks.create({
        title: task.title,
        priority: task.priority || 'medium',
        email_id: task.emailId || null,
      });
      if (res?.success && res.data) {
        setTasks(prev => [
          {
            id: res.data.id,
            title: res.data.title,
            priority: res.data.priority,
            done: res.data.done,
            dueDate: task.dueDate || 'Today',
            email_id: task.emailId || null,
          },
          ...prev,
        ]);
        toast.success('Task created successfully');
        return;
      }
    } catch {
      // Fallback local task creation
    }

    const newTask = {
      id: `task-${Date.now()}`,
      title: task.title,
      dueDate: task.dueDate || 'Today',
      priority: task.priority || 'medium',
      done: false,
      emailId: task.emailId || null,
    };
    setTasks(prev => [newTask, ...prev]);
    toast.success('Task saved');
  }, []);

  const deleteTask = useCallback(async (id) => {
    setTasks(prev => prev.filter(t => t.id !== id));
    try {
      await api.tasks.delete(id);
    } catch {
      // Local state updated
    }
  }, []);

  const sendEmail = useCallback(async (newEmail) => {
    try {
      const res = await api.emails.send({
        to: newEmail.to,
        subject: newEmail.subject,
        body: newEmail.body,
        draft_id: newEmail.draftId || null,
      });

      const sentObj = {
        id: res?.data?.id || `email-${Date.now()}`,
        from: { name: user.name, email: user.email, avatar: 'RK' },
        to: newEmail.to,
        subject: newEmail.subject,
        preview: newEmail.body.slice(0, 80),
        body: newEmail.body,
        time: 'Just now',
        date: new Date().toISOString().split('T')[0],
        category: 'Work',
        isRead: true,
        isStarred: false,
        isImportant: false,
        folder: 'sent',
        urgency: 'low',
        requiresReply: false,
        aiAnalysis: {
          confidence: 90,
          category: 'Work',
          priority: 'Normal',
          sentiment: 'Positive',
          requiresReply: false,
          keyPoints: ['Sent by user'],
          suspiciousFlag: false,
          extractedTasks: [],
          extractedDeadlines: [],
        },
      };

      setEmails(prev => [sentObj, ...prev]);
      setFolderCounts(prev => ({ ...prev, sent: (prev.sent || 0) + 1 }));
      toast.success('Email sent successfully');
    } catch (err) {
      toast.error(err.message || 'Failed to send email');
      throw err;
    }
  }, [user]);

  const updatePreferences = useCallback(async (newPref) => {
    try {
      const res = await api.preferences.update(newPref);
      if (res?.success) {
        setPreferences(prev => ({ ...prev, ...newPref }));
        toast.success('Preferences saved successfully');
      }
    } catch {
      toast.error('Could not save preferences to server');
    }
  }, []);

  const unreadNotifCount = notifications.filter(n => !n.read).length;

  const filteredEmails = emails.filter(email => {
    const matchFolder = (() => {
      if (activeFolder === 'inbox')     return email.folder === 'inbox';
      if (activeFolder === 'starred')   return email.isStarred;
      if (activeFolder === 'important') return email.isImportant;
      if (activeFolder === 'snoozed')   return email.folder === 'snoozed';
      if (activeFolder === 'sent')      return email.folder === 'sent';
      if (activeFolder === 'drafts')    return email.folder === 'drafts';
      return true;
    })();

    const matchFilter = (() => {
      if (activeFilter === 'all')          return true;
      if (activeFilter === 'important')    return email.isImportant;
      if (activeFilter === 'unread')       return !email.isRead;
      if (activeFilter === 'needs_reply')  return email.requiresReply;
      if (activeFilter === 'attachments')  return email.hasAttachments;
      return true;
    })();

    const matchSearch = !searchQuery ||
      email.subject?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      email.from?.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      email.preview?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      email.body?.toLowerCase().includes(searchQuery.toLowerCase());

    return matchFolder && matchFilter && matchSearch;
  });

  return (
    <AppContext.Provider value={{
      theme, toggleTheme,
      currentPage, setCurrentPage,
      user, setUser,
      emails, setEmails, filteredEmails,
      selectedEmail, setSelectedEmail,
      activeFolder, setActiveFolder,
      activeFilter, setActiveFilter,
      searchQuery, setSearchQuery,
      notifications, setNotifications, unreadNotifCount, dismissNotification, markAllNotificationsRead,
      sidebarOpen, setSidebarOpen,
      composing, setComposing,
      replyTone, setReplyTone,
      activePanel, setActivePanel,
      tasks, setTasks, toggleTask, addTask, deleteTask,
      deleteEmail,
      sendEmail,
      markAsRead, toggleStar,
      preferences, updatePreferences,
      integrationStatus, setIntegrationStatus,
      isMockData, isBackendConnected, loading,
      folderCounts,
      refreshInitialData: loadInitialData,
      syncGmail, syncing,
      currentThread, loadThread, loadingThread, selectEmailWithThread,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
};
