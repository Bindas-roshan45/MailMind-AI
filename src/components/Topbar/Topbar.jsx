import { useState } from 'react';
import {
  Search, Sun, Moon, Bell, Settings, Menu, X, ChevronDown,
  Command,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar, MockDataBanner } from '../ui';
import NotificationPanel from '../Notifications/NotificationPanel';

export default function Topbar() {
  const {
    user, theme, toggleTheme,
    searchQuery, setSearchQuery,
    unreadNotifCount, notifications, dismissNotification,
    sidebarOpen, setSidebarOpen,
    currentPage, setCurrentPage,
    isMockData,
  } = useApp();

  const [showNotif, setShowNotif]     = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  return (
    <header className="h-14 shrink-0 flex items-center justify-between gap-3 px-4 bg-white dark:bg-[#1E293B] border-b border-[#E5EAF2] dark:border-[#334155] z-20 transition-colors duration-150">
      {/* Left: Sidebar toggle + Search */}
      <div className="flex items-center gap-3 flex-1 max-w-xl">
        <button
          onClick={() => setSidebarOpen(prev => !prev)}
          className="p-1.5 rounded-lg text-[#7B8497] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        {/* Search bar */}
        <div className="relative flex-1 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7B8497] group-focus-within:text-[#4169E1] transition-colors" />
          <input
            type="text"
            placeholder="Search emails, subjects, contacts..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-[#F5F7FC] dark:bg-[#0F172A] border border-[#E5EAF2] dark:border-[#334155] rounded-lg pl-9 pr-14 py-1.5 text-xs sm:text-sm text-[#1E293B] dark:text-[#F8FAFC] placeholder-[#7B8497] dark:placeholder-[#64748B] outline-none focus:border-[#4169E1] focus:ring-1 focus:ring-[#4169E1]/20 transition-all"
          />
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 border border-[#E5EAF2] dark:border-slate-700 text-[10px] text-[#7B8497] font-medium pointer-events-none">
            <Command className="w-2.5 h-2.5" /> K
          </div>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2">
        {/* Gmail Connection Status Pill */}
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#F5F7FC] dark:bg-[#0F172A] border border-[#E5EAF2] dark:border-[#334155] text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-medium text-[#1E293B] dark:text-[#E2E8F0]">Gmail: Connected</span>
          <span className="text-[11px] text-[#7B8497] border-l border-[#E5EAF2] dark:border-slate-700 pl-2">Sync 2m ago</span>
        </div>

        {/* Mock data indicator */}
        {isMockData && <MockDataBanner />}

        {/* Dark / Light Mode Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-[#7B8497] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors border border-transparent hover:border-[#E5EAF2] dark:hover:border-[#334155]"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-[#7B8497]" />
          )}
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => {
              setShowNotif(prev => !prev);
              setShowProfile(false);
            }}
            className="p-2 rounded-lg text-[#7B8497] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors relative border border-transparent hover:border-[#E5EAF2] dark:hover:border-[#334155]"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadNotifCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#4169E1] rounded-full ring-2 ring-white dark:ring-[#1E293B]" />
            )}
          </button>
          {showNotif && (
            <NotificationPanel
              notifications={notifications}
              onDismiss={dismissNotification}
              onClose={() => setShowNotif(false)}
            />
          )}
        </div>

        {/* Settings button */}
        <button
          onClick={() => setCurrentPage('settings')}
          className={`p-2 rounded-lg transition-colors border ${
            currentPage === 'settings'
              ? 'bg-[#E8EEFF] text-[#4169E1] border-[#4169E1]/30 dark:bg-[#4169E1]/20 dark:text-[#93C5FD]'
              : 'text-[#7B8497] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] border-transparent hover:border-[#E5EAF2] dark:hover:border-[#334155]'
          }`}
          title="Settings"
          aria-label="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>

        {/* Profile Menu */}
        <div className="relative pl-1">
          <button
            onClick={() => {
              setShowProfile(prev => !prev);
              setShowNotif(false);
            }}
            className="flex items-center gap-2 p-1 pl-1.5 rounded-lg hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] border border-transparent hover:border-[#E5EAF2] dark:hover:border-[#334155] transition-all"
          >
            <Avatar name={user.name} size="sm" />
            <div className="hidden sm:block text-left pr-1">
              <p className="text-xs font-semibold text-[#1E293B] dark:text-white leading-none">{user.name}</p>
              <p className="text-[10px] text-[#7B8497] mt-0.5">{user.plan}</p>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-[#7B8497]" />
          </button>

          {showProfile && (
            <div className="absolute right-0 top-11 w-56 bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-dropdown p-2 z-50 animate-slide-down">
              <div className="px-3 py-2 border-b border-[#E5EAF2] dark:border-[#334155] mb-1">
                <p className="text-xs font-semibold text-[#1E293B] dark:text-white">{user.name}</p>
                <p className="text-[11px] text-[#7B8497] truncate">{user.email}</p>
                <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-medium bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD]">
                  {user.plan}
                </span>
              </div>
              <button
                onClick={() => {
                  setCurrentPage('settings');
                  setShowProfile(false);
                }}
                className="w-full text-left px-3 py-1.5 rounded-md text-xs text-[#1E293B] dark:text-[#E2E8F0] hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
              >
                Account Settings
              </button>
              <button
                onClick={() => {
                  setCurrentPage('analytics');
                  setShowProfile(false);
                }}
                className="w-full text-left px-3 py-1.5 rounded-md text-xs text-[#1E293B] dark:text-[#E2E8F0] hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
              >
                Analytics & Insights
              </button>
              <button
                onClick={() => {
                  setCurrentPage('tasks');
                  setShowProfile(false);
                }}
                className="w-full text-left px-3 py-1.5 rounded-md text-xs text-[#1E293B] dark:text-[#E2E8F0] hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
              >
                Upcoming Tasks
              </button>
              <div className="border-t border-[#E5EAF2] dark:border-[#334155] mt-1 pt-1">
                <button
                  onClick={() => setShowProfile(false)}
                  className="w-full text-left px-3 py-1.5 rounded-md text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
