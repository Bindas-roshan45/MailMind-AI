import { Star, Inbox } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar, CategoryBadge, EmptyState } from '../ui';

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
      <Avatar name={email.from.name} size="sm" className="mt-0.5" />

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
            {email.from.name}
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
  } = useApp();

  const handleSelect = (email) => {
    setSelectedEmail(email);
    markAsRead(email.id);
    if (onSelectMobile) onSelectMobile(email);
  };

  return (
    <div className="w-full md:w-80 lg:w-96 shrink-0 h-full flex flex-col bg-white dark:bg-[#1E293B] border-r border-[#E5EAF2] dark:border-[#334155] z-10">
      {/* Header & Filter Chips */}
      <div className="px-4 py-3 border-b border-[#E5EAF2] dark:border-[#334155] bg-white dark:bg-[#1E293B]">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-bold text-[#1E293B] dark:text-white capitalize">
            {activeFolder}
          </h2>
          <span className="text-xs text-[#7B8497] font-medium">
            {filteredEmails.length} {filteredEmails.length === 1 ? 'email' : 'emails'}
          </span>
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
        {filteredEmails.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No emails found"
            description="Try clearing your search query or selecting a different filter"
          />
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
