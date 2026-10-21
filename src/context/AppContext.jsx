import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { MOCK_EMAILS, MOCK_USER, MOCK_NOTIFICATIONS, FOLDER_COUNTS, MOCK_TASKS } from '../data/mockData';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [theme, setTheme]                   = useState(() => {
    return localStorage.getItem('mailmind_theme') || 'light';
  });
  const [currentPage, setCurrentPage]       = useState('inbox'); // 'inbox' | 'analytics' | 'tasks' | 'calendar' | 'settings'
  const [user, setUser]                     = useState(MOCK_USER);
  const [emails, setEmails]                 = useState(MOCK_EMAILS);
  const [selectedEmail, setSelectedEmail]   = useState(MOCK_EMAILS[0]);
  const [activeFolder, setActiveFolder]     = useState('inbox');
  const [activeFilter, setActiveFilter]     = useState('all');
  const [searchQuery, setSearchQuery]       = useState('');
  const [notifications, setNotifications]   = useState(MOCK_NOTIFICATIONS);
  const [sidebarOpen, setSidebarOpen]       = useState(true);
  const [composing, setComposing]           = useState(false);
  const [replyTone, setReplyTone]           = useState('professional');
  const [activePanel, setActivePanel]       = useState('ai_reply'); // 'ai_reply' | 'summary' | 'attachments' | 'thread'
  const [tasks, setTasks]                   = useState(MOCK_TASKS);
  const [isMockData]                        = useState(true);

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

  const markAsRead = useCallback((emailId) => {
    setEmails(prev => prev.map(e => e.id === emailId ? { ...e, isRead: true } : e));
  }, []);

  const toggleStar = useCallback((emailId) => {
    setEmails(prev => prev.map(e => e.id === emailId ? { ...e, isStarred: !e.isStarred } : e));
  }, []);

  const dismissNotification = useCallback((notifId) => {
    setNotifications(prev => prev.map(n => n.id === notifId ? { ...n, read: true } : n));
  }, []);

  const toggleTask = useCallback((id) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
  }, []);

  const addTask = useCallback((task) => {
    const newTask = {
      id: `task-${Date.now()}`,
      title: task.title,
      dueDate: task.dueDate || 'Today',
      priority: task.priority || 'medium',
      done: false,
      emailId: task.emailId || null,
    };
    setTasks(prev => [newTask, ...prev]);
  }, []);

  const deleteTask = useCallback((id) => {
    setTasks(prev => prev.filter(t => t.id !== id));
  }, []);

  const sendEmail = useCallback((newEmail) => {
    const emailObj = {
      id: `email-${Date.now()}`,
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
    setEmails(prev => [emailObj, ...prev]);
  }, [user]);

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
      email.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      email.from.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      email.preview.toLowerCase().includes(searchQuery.toLowerCase()) ||
      email.body.toLowerCase().includes(searchQuery.toLowerCase());

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
      notifications, setNotifications, unreadNotifCount, dismissNotification,
      sidebarOpen, setSidebarOpen,
      composing, setComposing,
      replyTone, setReplyTone,
      activePanel, setActivePanel,
      tasks, setTasks, toggleTask, addTask, deleteTask,
      sendEmail,
      markAsRead, toggleStar,
      isMockData,
      folderCounts: FOLDER_COUNTS,
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
