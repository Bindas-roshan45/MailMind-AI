import React, { useState } from 'react';
import {
  ShieldAlert,
  Edit3,
  Send,
  X,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function SensitiveApprovalModal({
  isOpen,
  onClose,
  email,
  initialDraft = '',
  sensitivityReason = 'Requires human review',
  onSendSuccess,
  sendEmailFn,
}) {
  const [replyText, setReplyText] = useState(initialDraft || email?.ai_suggested_reply || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isSent, setIsSent] = useState(false);

  if (!isOpen || !email) return null;

  const senderName = email?.from_name || email?.from?.name || (typeof email?.from === 'string' ? email.from : 'Sender');
  const senderEmail = email?.from_email || email?.from?.email || email?.to || '';
  const subject = email?.subject || 'No Subject';

  const handleSend = async () => {
    if (!replyText.trim()) {
      toast.error('Reply text cannot be empty');
      return;
    }

    setIsSending(true);
    try {
      if (sendEmailFn) {
        await sendEmailFn({
          to: senderEmail,
          subject: subject.startsWith('Re:') ? subject : `Re: ${subject}`,
          body: replyText,
          threadId: email?.thread_id || email?.threadId || null,
        });
      }
      setIsSent(true);
      toast.success('Approved reply sent securely via Gmail');
      if (onSendSuccess) {
        onSendSuccess(replyText);
      }
      setTimeout(() => {
        setIsSent(false);
        onClose();
      }, 1400);
    } catch (err) {
      toast.error(err?.message || 'Failed to dispatch email');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="sensitive-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
    >
      <div className="relative w-full max-w-2xl bg-white dark:bg-[#1E293B] rounded-2xl shadow-2xl border border-amber-300 dark:border-amber-600/40 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Sensitive Warning Banner */}
        <div className="bg-gradient-to-r from-amber-500/15 via-orange-500/10 to-amber-500/5 dark:from-amber-950/40 dark:to-slate-900 border-b border-amber-200 dark:border-amber-800/40 px-6 py-4 flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-600 dark:text-amber-400 shrink-0">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-300/40">
                Approval Required
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Safety Guardrail Triggered
              </span>
            </div>
            <h2 id="sensitive-modal-title" className="text-lg font-bold text-slate-900 dark:text-white mt-1">
              Sensitive Email Reply Review
            </h2>
            <p className="text-xs text-amber-800 dark:text-amber-200/90 mt-0.5 flex items-center gap-1.5 font-medium">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              {sensitivityReason}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSending}
            aria-label="Close review dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Email Context Header */}
        <div className="px-6 py-3.5 bg-slate-50 dark:bg-slate-900/60 border-b border-slate-200 dark:border-slate-800 text-xs space-y-1">
          <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
            <span className="font-medium text-slate-500 dark:text-slate-400">From:</span>
            <span className="font-semibold text-slate-800 dark:text-slate-100 truncate max-w-md">
              {senderName} &lt;{senderEmail}&gt;
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-600 dark:text-slate-300">
            <span className="font-medium text-slate-500 dark:text-slate-400">Subject:</span>
            <span className="font-medium text-slate-800 dark:text-slate-200 truncate max-w-md">
              {subject}
            </span>
          </div>
        </div>

        {/* Reply Body Editor */}
        <div className="p-6 flex-1 overflow-y-auto space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
              Proposed AI Reply ({isEditing ? 'Editing Mode' : 'Read-only Preview'})
            </label>
            {!isEditing ? (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
              >
                <Edit3 className="w-3.5 h-3.5" />
                Edit Reply Text
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="text-xs font-medium text-slate-600 dark:text-slate-300 hover:underline"
              >
                Done Editing
              </button>
            )}
          </div>

          {isEditing ? (
            <textarea
              rows={8}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Edit your response before sending..."
              className="w-full text-sm p-4 rounded-xl border border-blue-400 dark:border-blue-500 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-inner font-sans leading-relaxed"
            />
          ) : (
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/50 text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap font-sans leading-relaxed min-h-[160px] shadow-sm">
              {replyText || <span className="text-slate-400 italic">No reply drafted yet. Click Edit to type a message.</span>}
            </div>
          )}

          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>Character count: {replyText.length}</span>
            <span>Safety Rule: Sensitive content requires explicit user approval</span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/80 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSending}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          >
            Cancel (Do Not Send)
          </button>

          <div className="flex items-center gap-2">
            {!isEditing && (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                disabled={isSending || isSent}
                className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5"
              >
                <Edit3 className="w-3.5 h-3.5" />
                Edit
              </button>
            )}

            <button
              type="button"
              onClick={handleSend}
              disabled={isSending || isSent || !replyText.trim()}
              className={`px-5 py-2 rounded-xl text-xs font-semibold text-white shadow-md flex items-center gap-2 transition-all ${
                isSent
                  ? 'bg-emerald-600'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50'
              }`}
            >
              {isSending ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  <span>Sending...</span>
                </>
              ) : isSent ? (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Sent Successfully</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Approve & Send</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
