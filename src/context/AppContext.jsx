import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { MOCK_EMAILS, MOCK_USER, MOCK_NOTIFICATIONS, FOLDER_COUNTS, MOCK_TASKS } from '../data/mockData';
import api from '../services/api';
import toast from 'react-hot-toast';

const AppContext = createContext(null);

const mapBackendEmail = (e) => ({
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
});

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
  const [backgroundSyncing, setBackgroundSyncing] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  const [syncError, setSyncError] = useState(null);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [isMockData, setIsMockData] = useState(true);
  const [currentThread, setCurrentThread] = useState(null);
  const [loadingThread, setLoadingThread] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  // Synchronization refs to prevent overlapping requests and closure staleness
  const isSyncInProgressRef = useRef(false);
  const selectedEmailRef = useRef(selectedEmail);
  const emailsRef = useRef(emails);
  const integrationStatusRef = useRef(integrationStatus);

  useEffect(() => {
    selectedEmailRef.current = selectedEmail;
  }, [selectedEmail]);
  useEffect(() => {
    emailsRef.current = emails;
  }, [emails]);
  useEffect(() => {
    integrationStatusRef.current = integrationStatus;
  }, [integrationStatus]);

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

  // ── Real-Time Incremental Inbox Sync (Does Not Reset User State) ──
  const refreshEmails = useCallback(async ({ silent = false, forceSync = false } = {}) => {
    if (!localStorage.getItem('mailmind_token')) {
      return { success: false, reason: 'unauthenticated' };
    }

    if (isSyncInProgressRef.current) {
      return { success: false, inProgress: true };
    }
    isSyncInProgressRef.current = true;

    if (!silent) setSyncing(true);
    setBackgroundSyncing(true);

    try {
      const isConnected = Boolean(integrationStatusRef.current?.is_connected);

      // If Gmail is actively connected, trigger Gmail inbox sync
      if (isConnected) {
        try {
          const syncRes = await api.emails.sync(25, forceSync);
          if (syncRes?.data?.reconnect_required) {
            setIntegrationStatus(prev => ({ ...prev, is_connected: false, account_status: 'error' }));
            toast.error('Gmail authorization expired or was revoked. Please reconnect in Settings.');
          }
        } catch (syncErr) {
          if (syncErr?.status === 401 || syncErr?.message?.includes('reconnect')) {
            setIntegrationStatus(prev => ({ ...prev, is_connected: false, account_status: 'error' }));
            toast.error('Gmail authorization expired. Please reconnect in Settings.');
          } else if (syncErr?.status === 429) {
            console.warn('Gmail API rate limit reached, will retry on next polling cycle.');
          } else {
            console.warn('Background sync encountered network or server notice:', syncErr);
          }
        }
      }

      // Fetch fresh email list, unread counts, and notifications from database
      const [emailRes, notifsRes] = await Promise.all([
        api.emails.list().catch(() => null),
        api.notifications.list().catch(() => null),
      ]);

      if (emailRes?.success && emailRes.data?.items) {
        const rawItems = emailRes.data.items || [];
        const mappedEmails = rawItems.map(mapBackendEmail);

        // Detect newly arrived messages for alert and unread updates
        const prevEmailIds = new Set(emailsRef.current.map(e => e.messageId || e.id));
        const newEmails = mappedEmails.filter(e => !prevEmailIds.has(e.messageId || e.id));

        if (newEmails.length > 0 && prevEmailIds.size > 0 && silent) {
          if (newEmails.length === 1) {
            const sender = newEmails[0].from?.name || newEmails[0].from?.email || 'New sender';
            toast.success(`New email from ${sender}: "${newEmails[0].subject.slice(0, 45)}"`, {
              icon: '📩',
              duration: 4500,
            });
          } else {
            toast.success(`${newEmails.length} new emails arrived in your inbox`, {
              icon: '📩',
              duration: 4500,
            });
          }
        }

        // Update email collection
        setEmails(mappedEmails);

        // Preserve selected email if still present in the list; otherwise select first only if empty
        const currentSelected = selectedEmailRef.current;
        if (currentSelected) {
          const matchingUpdated = mappedEmails.find(
            e => e.id === currentSelected.id || (e.messageId && e.messageId === currentSelected.messageId)
          );
          if (matchingUpdated) {
            setSelectedEmail(matchingUpdated);
          }
        } else if (mappedEmails.length > 0) {
          setSelectedEmail(mappedEmails[0]);
        }

        if (emailRes.data.folder_counts) {
          setFolderCounts(emailRes.data.folder_counts);
        }
      }

      // Update notifications
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

      setLastSyncedAt(new Date());
      setSyncError(null);
      return { success: true };
    } catch (err) {
      console.warn('Real-time sync error:', err);
      setSyncError(err?.message || 'Sync failed');
      return { success: false, error: err };
    } finally {
      isSyncInProgressRef.current = false;
      if (!silent) setSyncing(false);
      setBackgroundSyncing(false);
    }
  }, []);

  // ── Load Real Data from Backend on Initial Mount ──
  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      let token = localStorage.getItem('mailmind_token');
      if (!token) {
        const tokenRes = await api.auth.getDemoToken().catch(() => null);
        if (tokenRes?.access_token) {
          token = tokenRes.access_token;
          localStorage.setItem('mailmind_token', token);
        }
      }

      // If no valid token in staging/production mode, prompt sign-in without calling protected endpoints
      if (!token) {
        setUser(null);
        setAuthModalOpen(true);
        setIsBackendConnected(true);
        return;
      }

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
        setAuthModalOpen(false);
      } else {
        setUser(null);
        setAuthModalOpen(true);
      }

      // Fetch emails & tasks only when a valid token exists
      if (localStorage.getItem('mailmind_token') || userRes?.success) {
        await refreshEmails({ silent: true, forceSync: false });

        const tasksRes = await api.tasks.list().catch(() => null);
        if (tasksRes?.success && tasksRes.data) {
          setTasks(tasksRes.data);
        }
      }

      setIsBackendConnected(true);
    } catch (err) {
      console.warn('Backend unavailable or network error, running in local fallback mode:', err);
      setIsBackendConnected(false);
    } finally {
      setLoading(false);
    }
  }, [refreshEmails]);

  // ── Session & Logout Handling ──
  const logout = useCallback(() => {
    localStorage.removeItem('mailmind_token');
    setUser(null);
    setEmails([]);
    setNotifications([]);
    setTasks([]);
    setAuthModalOpen(true);
    toast.success('Signed out successfully.');
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      setAuthModalOpen(true);
    };
    window.addEventListener('mailmind:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('mailmind:unauthorized', handleUnauthorized);
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // ── Automatic Background Polling & Visibility Synchronization ──
  useEffect(() => {
    // Poll every 45 seconds while app is open (within 30-60s requirement)
    const POLL_INTERVAL_MS = 45000;

    const timer = setInterval(() => {
      if (localStorage.getItem('mailmind_token')) {
        refreshEmails({ silent: true, forceSync: false });
      }
    }, POLL_INTERVAL_MS);

    // Synchronize automatically when user switches back into this browser tab
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && localStorage.getItem('mailmind_token')) {
        refreshEmails({ silent: true, forceSync: false });
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [refreshEmails]);

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

  // ── Manual User-Triggered Sync ──
  const syncGmail = useCallback(async () => {
    const syncToast = toast.loading('Syncing with Gmail...');
    try {
      const res = await refreshEmails({ silent: false, forceSync: true });
      if (res?.success) {
        toast.success('Inbox updated from Gmail', { id: syncToast });
      } else if (res?.inProgress) {
        toast.success('Sync already in progress...', { id: syncToast });
      } else {
        toast.error('Sync completed with warnings', { id: syncToast });
      }
    } catch (err) {
      toast.error(err.message || 'Sync error', { id: syncToast });
    }
  }, [refreshEmails]);

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
      if (activeFolder === 'archive')   return email.folder === 'archive';
      if (activeFolder === 'spam')      return email.folder === 'spam';
      if (activeFolder === 'trash')     return email.folder === 'trash';
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
      backgroundSyncing, lastSyncedAt, syncError, refreshEmails,
      currentThread, loadThread, loadingThread, selectEmailWithThread,
      authModalOpen, setAuthModalOpen, logout,
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
