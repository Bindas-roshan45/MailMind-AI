import { useState, useEffect } from 'react';
import { X, Eye, Sparkles } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function PushNotificationToast() {
  const { notifications, setSelectedEmail, emails } = useApp();
  const [shown, setShown] = useState([]);
  const [dismissed, setDismissed] = useState(new Set());

  useEffect(() => {
    const unread = notifications.filter(n => !n.read && !dismissed.has(n.id));
    if (unread.length > 0 && shown.length === 0) {
      setShown(unread.slice(0, 1)); // Show 1 clean toast at a time
    }
  }, [notifications, dismissed, shown.length]);

  const handleView = (notif) => {
    if (notif.emailId) {
      const email = emails.find(e => e.id === notif.emailId);
      if (email) setSelectedEmail(email);
    }
    dismiss(notif.id);
  };

  const dismiss = (id) => {
    setDismissed(prev => new Set([...prev, id]));
    setShown(prev => prev.filter(n => n.id !== id));
  };

  if (shown.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm" role="status" aria-live="polite">
      {shown.map(notif => (
        <div
          key={notif.id}
          className="bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-modal p-3.5 animate-slide-up"
        >
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#E8EEFF] dark:bg-[#4169E1]/20 text-[#4169E1] dark:text-[#93C5FD] flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#1E293B] dark:text-white">
                  {notif.title}
                </span>
                <button
                  onClick={() => dismiss(notif.id)}
                  className="text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white p-0.5 rounded"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <p className="text-xs text-[#7B8497] dark:text-[#94A3B8] mt-1 leading-snug line-clamp-2">
                {notif.body}
              </p>

              <div className="flex items-center gap-2 mt-2.5">
                <button
                  onClick={() => handleView(notif)}
                  className="px-2.5 py-1 rounded-md bg-[#4169E1] hover:bg-[#3457C8] text-white text-xs font-semibold flex items-center gap-1 transition-colors"
                >
                  <Eye className="w-3 h-3" /> View
                </button>
                <button
                  onClick={() => dismiss(notif.id)}
                  className="px-2.5 py-1 rounded-md text-xs font-medium text-[#7B8497] hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
