import { X, Bell, Sparkles, Clock } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function NotificationPanel({ notifications, onDismiss, onClose }) {
  const { setSelectedEmail, emails } = useApp();

  const handleClick = (notif) => {
    if (notif.emailId) {
      const email = emails.find(e => e.id === notif.emailId);
      if (email) setSelectedEmail(email);
    }
    onDismiss(notif.id);
    onClose();
  };

  const handleMarkAllRead = () => {
    notifications.forEach(n => onDismiss(n.id));
  };

  return (
    <div className="absolute right-0 top-12 w-80 bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-dropdown z-50 overflow-hidden animate-slide-down">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5EAF2] dark:border-[#334155]">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-[#4169E1]" />
          <span className="text-xs font-bold text-[#1E293B] dark:text-white">Notifications</span>
          <span className="text-[10px] font-semibold bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD] px-1.5 py-0.2 rounded-full">
            {notifications.filter(n => !n.read).length}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white p-1 rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="max-h-72 overflow-y-auto divide-y divide-[#E5EAF2] dark:divide-[#334155]">
        {notifications.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#7B8497]">No new notifications</div>
        ) : (
          notifications.map(notif => (
            <div
              key={notif.id}
              onClick={() => handleClick(notif)}
              className={`p-3 cursor-pointer hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors flex items-start gap-2.5 ${
                !notif.read ? 'bg-[#F8FAFC] dark:bg-[#131E31]/40' : ''
              }`}
            >
              <div className="w-7 h-7 rounded-lg bg-[#E8EEFF] dark:bg-[#4169E1]/20 text-[#4169E1] dark:text-[#93C5FD] flex items-center justify-center shrink-0 mt-0.5">
                {notif.type === 'ai_draft' ? (
                  <Sparkles className="w-3.5 h-3.5" />
                ) : (
                  <Clock className="w-3.5 h-3.5" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white truncate">
                    {notif.title}
                  </p>
                  <span className="text-[10px] text-[#7B8497] shrink-0">{notif.time}</span>
                </div>
                <p className="text-[11px] text-[#7B8497] dark:text-[#94A3B8] mt-0.5 line-clamp-2 leading-tight">
                  {notif.body}
                </p>
              </div>
              {!notif.read && (
                <span className="w-1.5 h-1.5 rounded-full bg-[#4169E1] shrink-0 mt-2" />
              )}
            </div>
          ))
        )}
      </div>

      {notifications.length > 0 && (
        <div className="p-2 border-t border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31]">
          <button
            onClick={handleMarkAllRead}
            className="w-full text-center py-1 text-xs font-semibold text-[#4169E1] hover:underline"
          >
            Mark all as read
          </button>
        </div>
      )}
    </div>
  );
}
