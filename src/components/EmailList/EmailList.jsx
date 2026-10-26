import { Star, Inbox, RefreshCw } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar, CategoryBadge, EmptyState } from '../ui';
import { formatLastSynced } from '../../utils/date';

const FILTERS = [
  { id: 'all',          label: 'All' },
  { id: 'unread',       label: 'Unread' },
  { id: 'needs_reply',  label: 'Needs Reply' },
  { id: 'important',    label: 'Important' },
];

function EmailRow({ email, isSelected, onClick, onStar }) {
  return (
    <div
      onClick={() => onClick(email)}
      className={`
        w-full flex items-start gap-3 px-4 py-3.5 text-left border-b border-[#E5EAF2] dark:border-[#334155]
        transition-all duration-150 group cursor-pointer relative
        ${isSelected
          ? 'bg-[#E8EEFF] dark:bg-[#4169E1]/15 border-l-4 border-l-[#4169E1]'
          : 'bg-white dark:bg-[#1E293B] hover:bg-[#F8FAFC] dark:hover:bg-[#28384E] border-l-4 border-l-transparent'
        }
      `}
    >
      {/* Unread indicator */}
      {!email.isRead && (
        <span className="absolute left-1 top-4 w-1.5 h-1.5 bg-[#4169E1] rounded-full" />
      )}

      {/* Avatar */}
      <Avatar name={email.from?.name || 'User'} size="sm" className="mt-0.5" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1 mb-1">
          <span
            className={`text-xs truncate ${
              !email.isRead
                ? 'font-bold text-[#1E293B] dark:text-white'
                : 'font-medium text-[#475569] dark:text-[#CBD5E1]'
            }`}
          >
            {email.from?.name || email.from?.email || 'Unknown'}
          </span>
          <span className="text-[11px] text-[#7B8497] dark:text-[#94A3B8] shrink-0 font-normal">
            {email.time}
          </span>
        </div>

        <p
          className={`text-xs truncate mb-1 ${
            !email.isRead
              ? 'font-semibold text-[#1E293B] dark:text-white'
              : 'font-normal text-[#334155] dark:text-[#CBD5E1]'
          }`}
        >
          {email.subject}
        </p>

        <p className="text-[11px] text-[#7B8497] dark:text-[#94A3B8] truncate leading-tight">
          {email.preview}
        </p>

        {/* Badges */}
        <div className="flex items-center gap-1.5 mt-2 flex-wrap">
          <CategoryBadge category={email.category} size="xs" />
          {email.requiresReply && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD]">
              Needs Reply
            </span>
          )}
          {email.urgency === 'urgent' && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-300">
              Urgent
            </span>
          )}
        </div>
      </div>

      {/* Star button */}
      <button
        type="button"
        onClick={e => {
          e.stopPropagation();
          onStar(email.id);
        }}
        className="shrink-0 p-1 text-[#CBD5E1] dark:text-slate-600 hover:text-amber-400 dark:hover:text-amber-400 transition-colors"
        aria-label={email.isStarred ? 'Unstar' : 'Star'}
      >
        <Star
          className={`w-4 h-4 ${
            email.isStarred ? 'text-amber-400 fill-amber-400' : ''
          }`}
        />
      </button>
    </div>
  );
}

export default function EmailList({ onSelectMobile }) {
  const {
    filteredEmails, selectedEmail, setSelectedEmail,
    activeFilter, setActiveFilter,
    activeFolder,
    toggleStar, markAsRead,
    syncGmail, syncing, loading, integrationStatus,
    selectEmailWithThread,
    lastSyncedAt, backgroundSyncing,
  } = useApp();

  const handleSelect = (email) => {
    if (selectEmailWithThread) {
      selectEmailWithThread(email);
    } else {
      setSelectedEmail(email);
    }
    markAsRead(email.id);
    if (onSelectMobile) onSelectMobile(email);
  };

  return (
    <div className="w-full md:w-80 lg:w-96 shrink-0 h-full flex flex-col bg-white dark:bg-[#1E293B] border-r border-[#E5EAF2] dark:border-[#334155] z-10">
      {/* Header & Filter Chips */}
      <div className="px-4 py-3 border-b border-[#E5EAF2] dark:border-[#334155] bg-white dark:bg-[#1E293B]">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-[#1E293B] dark:text-white capitalize">
              {activeFolder}
            </h2>
            {integrationStatus?.is_connected && (
              <span className="w-2 h-2 rounded-full bg-emerald-500" title="Connected to Gmail" />
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-end">
              <span className="text-xs text-[#7B8497] font-medium leading-none">
                {filteredEmails.length} {filteredEmails.length === 1 ? 'email' : 'emails'}
              </span>
              {lastSyncedAt && (
                <span className="text-[10px] text-[#94A3B8] dark:text-[#64748B] mt-0.5">
                  {backgroundSyncing ? 'Syncing...' : formatLastSynced(lastSyncedAt)}
                </span>
              )}
            </div>
            <button
              onClick={() => syncGmail()}
              disabled={syncing || backgroundSyncing}
              className={`p-1.5 rounded-lg border border-[#E5EAF2] dark:border-[#334155] text-[#7B8497] hover:text-[#4169E1] hover:border-[#4169E1] transition-all ${
                (syncing || backgroundSyncing) ? 'animate-spin text-[#4169E1]' : ''
              }`}
              title={lastSyncedAt ? `Last synced: ${new Date(lastSyncedAt).toLocaleTimeString()}` : "Sync Inbox with Gmail"}
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-0.5">
          {FILTERS.map(f => {
            const isActive = activeFilter === f.id;
            return (
              <button
                key={f.id}
                onClick={() => setActiveFilter(f.id)}
                className={`
                  px-2.5 py-1 text-xs font-medium rounded-lg transition-all shrink-0
                  ${isActive
                    ? 'bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD] font-semibold'
                    : 'text-[#7B8497] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E]'
                  }
                `}
              >
                {f.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Email rows list */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#E5EAF2] dark:divide-[#334155]">
        {loading && filteredEmails.length === 0 ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4, 5].map(n => (
              <div key={n} className="animate-pulse flex items-start gap-3 py-2">
                <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
                  <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-4/5" />
                  <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredEmails.length === 0 ? (
          <div className="p-6 text-center space-y-3">
            <EmptyState
              icon={Inbox}
              title={integrationStatus?.is_connected ? "No emails in this view" : "No emails found"}
              description={
                integrationStatus?.is_connected
                  ? "Your Gmail inbox is up to date. Click sync to check for new messages."
                  : "Try clearing filters or connect Gmail in Settings."
              }
            />
            {integrationStatus?.is_connected && (
              <button
                onClick={() => syncGmail()}
                disabled={syncing}
                className="btn-secondary text-xs py-1.5 px-3 mx-auto flex items-center gap-1.5 shadow-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                <span>{syncing ? 'Checking Gmail...' : 'Sync Gmail Now'}</span>
              </button>
            )}
          </div>
        ) : (
          filteredEmails.map(email => (
            <EmailRow
              key={email.id}
              email={email}
              isSelected={selectedEmail?.id === email.id}
              onClick={handleSelect}
              onStar={toggleStar}
            />
          ))
        )}
      </div>
    </div>
  );
}
