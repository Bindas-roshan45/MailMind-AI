import { useState } from 'react';
import {
  Inbox, Star, AlertCircle, Clock, Send, FileText,
  BarChart2, BarChart3, CheckSquare, Calendar, Settings,
  Plus, ChevronDown, ChevronRight,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { MOCK_LABELS } from '../../data/mockData';

const FOLDER_NAV = [
  { id: 'inbox',     label: 'Inbox',     icon: Inbox },
  { id: 'starred',   label: 'Starred',   icon: Star },
  { id: 'important', label: 'Important', icon: AlertCircle },
  { id: 'snoozed',   label: 'Snoozed',   icon: Clock },
  { id: 'sent',      label: 'Sent',      icon: Send },
  { id: 'drafts',    label: 'Drafts',    icon: FileText },
];

const PAGES_NAV = [
  { id: 'analytics', label: 'Analytics', icon: BarChart2 },
  { id: 'tasks',     label: 'Tasks',     icon: CheckSquare, badge: 4 },
  { id: 'reports',   label: 'Reports',   icon: BarChart3 },
  { id: 'calendar',  label: 'Calendar',  icon: Calendar },
  { id: 'settings',  label: 'Settings',  icon: Settings },
];

export default function Sidebar() {
  const {
    activeFolder, setActiveFolder,
    currentPage, setCurrentPage,
    folderCounts, user,
    sidebarOpen, setSidebarOpen,
    setComposing,
  } = useApp();

  const [labelsExpanded, setLabelsExpanded] = useState(true);

  if (!sidebarOpen) return null;

  const handleFolderClick = (folderId) => {
    setCurrentPage('inbox');
    setActiveFolder(folderId);
    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  const handlePageClick = (pageId) => {
    setCurrentPage(pageId);
    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      <div
        onClick={() => setSidebarOpen(false)}
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-30 lg:hidden"
      />
      <aside className="fixed lg:static inset-y-0 left-0 w-60 shrink-0 h-full flex flex-col bg-[#17243B] text-[#E2E8F0] border-r border-[#223554] z-40 select-none shadow-xl lg:shadow-none">
        {/* Brand Header */}
        <div className="px-4 py-4 border-b border-[#223554] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#4169E1] flex items-center justify-center text-white font-bold text-sm shadow-sm">
              M
            </div>
            <div>
              <h1 className="font-semibold text-white text-sm tracking-tight leading-none">MailMind AI</h1>
              <p className="text-[11px] text-[#94A3B8] mt-1 font-normal">Smart Email Agent</p>
            </div>
          </div>
        </div>

        {/* Primary Action: Compose */}
        <div className="px-3 py-3">
          <button
            onClick={() => setComposing(true)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-[#4169E1] hover:bg-[#3457C8] text-white text-xs font-semibold shadow-sm transition-all duration-150 active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>New Email</span>
          </button>
        </div>

        {/* Navigation List */}
        <nav className="flex-1 px-3 py-1 space-y-5 overflow-y-auto no-scrollbar">
          {/* Core Folders */}
          <div>
            <p className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#7B8FA8]">
              Mailboxes
            </p>
            <div className="space-y-0.5">
              {FOLDER_NAV.map(item => {
                const Icon = item.icon;
                const count = folderCounts[item.id] || 0;
                const isActive = currentPage === 'inbox' && activeFolder === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleFolderClick(item.id)}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-[#4169E1] text-white shadow-sm font-semibold'
                        : 'text-[#94A3B8] hover:text-white hover:bg-[#1F314F]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className="w-4 h-4 shrink-0" />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {count > 0 && (
                      <span
                        className={`text-[10px] font-medium px-1.5 py-0.2 rounded-full ${
                          isActive
                            ? 'bg-white/20 text-white'
                            : 'bg-[#223554] text-[#CBD5E1]'
                        }`}
                      >
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Dedicated Pages */}
          <div>
            <p className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#7B8FA8]">
              Workspace
            </p>
            <div className="space-y-0.5">
              {PAGES_NAV.map(item => {
                const Icon = item.icon;
                const isActive = currentPage === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handlePageClick(item.id)}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-[#4169E1] text-white shadow-sm font-semibold'
                        : 'text-[#94A3B8] hover:text-white hover:bg-[#1F314F]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className="w-4 h-4 shrink-0" />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`text-[10px] font-medium px-1.5 py-0.2 rounded-full ${
                          isActive
                            ? 'bg-white/20 text-white'
                            : 'bg-[#223554] text-[#CBD5E1]'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Labels / Categories */}
          <div>
            <button
              onClick={() => setLabelsExpanded(prev => !prev)}
              className="w-full flex items-center justify-between px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#7B8FA8] hover:text-[#CBD5E1]"
            >
              <span>Labels</span>
              {labelsExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
            {labelsExpanded && (
              <div className="space-y-0.5">
                {MOCK_LABELS.map(label => (
                  <button
                    key={label.id}
                    onClick={() => {
                      setCurrentPage('inbox');
                      setActiveFolder('inbox');
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-[#94A3B8] hover:text-white hover:bg-[#1F314F] transition-colors"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: label.color }}
                      />
                      <span className="truncate">{label.name}</span>
                    </div>
                    <span className="text-[10px] text-[#64748B]">{label.count}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </nav>

        {/* Gmail Account Status Footer */}
        <div className="p-3 border-t border-[#223554] bg-[#131E31]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-[#1F314F] border border-[#2B4368] flex items-center justify-center text-xs font-semibold text-white">
              {user.name.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate leading-tight">{user.email}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span className="text-[10px] text-[#94A3B8]">Gmail Connected</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
