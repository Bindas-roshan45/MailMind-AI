import { useState } from 'react';
import {
  Star, Reply, Trash2,
  Archive, Clock, RotateCcw, Send, Save,
  MessageSquare, Paperclip, GitBranch,
  Lightbulb, CheckCircle2, AlertCircle, TrendingUp,
  Globe, ShrinkIcon, Expand, Sparkles, Check, Plus, ArrowLeft,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar, CategoryBadge } from '../ui';
import toast from 'react-hot-toast';

// ─── AI Analysis Panel ──────────────────────────────────────
function AIAnalysisCard({ analysis }) {
  if (!analysis) return null;
  const { confidence, priority, sentiment, keyPoints, suspiciousFlag } = analysis;

  return (
    <div className="card-white p-3.5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-[#E8EEFF] dark:bg-[#4169E1]/20 flex items-center justify-center text-[#4169E1] dark:text-[#93C5FD]">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-[#1E293B] dark:text-white">AI Analysis</span>
        </div>
        <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800/40">
          {confidence}% confidence
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-[#F5F7FC] dark:bg-[#0F172A] p-2 rounded-lg border border-[#E5EAF2] dark:border-[#334155]">
          <span className="text-[10px] text-[#7B8497] block">Priority</span>
          <span className="font-semibold text-[#1E293B] dark:text-white">{priority}</span>
        </div>
        <div className="bg-[#F5F7FC] dark:bg-[#0F172A] p-2 rounded-lg border border-[#E5EAF2] dark:border-[#334155]">
          <span className="text-[10px] text-[#7B8497] block">Sentiment</span>
          <span className="font-semibold text-[#1E293B] dark:text-white">{sentiment}</span>
        </div>
      </div>

      {suspiciousFlag && (
        <div className="flex items-center gap-2 p-2 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-700 dark:text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>Potential phishing or suspicious email</span>
        </div>
      )}

      {keyPoints?.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[#7B8497]">
            Key Takeaways
          </p>
          <ul className="space-y-1">
            {keyPoints.map((pt, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-[#334155] dark:text-[#CBD5E1]">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                <span>{pt}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── AI Reply Panel ─────────────────────────────────────────
function AIReplyPanel({ email }) {
  const [tone, setTone]             = useState('professional');
  const [language, setLanguage]     = useState('english');
  const [reply, setReply]           = useState(email?.suggestedReply || '');
  const [generating, setGenerating] = useState(false);
  const [sent, setSent]             = useState(false);

  const tones = ['Professional', 'Friendly', 'Short', 'Detailed'];
  const langs = ['English', 'Hindi', 'Hinglish'];

  const handleRegenerate = () => {
    setGenerating(true);
    setTimeout(() => {
      setReply(
        `Hi ${email?.from?.name?.split(' ')[0] || 'there'},\n\nThank you for getting in touch. I have reviewed your request and would be delighted to assist.\n\nPlease let me know a suitable time for a quick 10-minute touchpoint this week.\n\nBest regards,\nRoshan`
      );
      setGenerating(false);
      toast.success('Generated fresh AI reply');
    }, 900);
  };

  const handleSend = () => {
    setSent(true);
    toast.success('Reply sent successfully!');
    setTimeout(() => setSent(false), 3000);
  };

  const handleModify = (type) => {
    if (type === 'shorten') {
      setReply(`Hi ${email?.from?.name?.split(' ')[0] || 'there'},\n\nThanks for your email. I agree with your proposal and will send the details shortly.\n\nBest,\nRoshan`);
    } else if (type === 'expand') {
      setReply(prev => `${prev}\n\nAdditionally, please feel free to let me know if you require any specific adjustments to the timeline or scope of work.`);
    } else if (type === 'improve') {
      toast.success('Polished tone and clarity');
    }
  };

  return (
    <div className="card-white overflow-hidden space-y-0">
      {/* Tone & Options Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31] flex-wrap gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-medium text-[#7B8497] mr-1">Tone:</span>
          {tones.map(t => {
            const isActive = tone === t.toLowerCase();
            return (
              <button
                key={t}
                onClick={() => setTone(t.toLowerCase())}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors ${
                  isActive
                    ? 'bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD] font-semibold'
                    : 'text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white'
                }`}
              >
                {t}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs text-[#7B8497]">
            <Globe className="w-3.5 h-3.5" />
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              className="bg-transparent text-xs text-[#1E293B] dark:text-[#CBD5E1] outline-none cursor-pointer"
            >
              {langs.map(l => (
                <option key={l} value={l.toLowerCase()} className="bg-white dark:bg-slate-800">
                  {l}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRegenerate}
            disabled={generating}
            className="btn-ghost text-xs py-1 px-2 flex items-center gap-1 text-[#4169E1] dark:text-[#93C5FD]"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Editor Body */}
      <div className="p-4">
        {generating ? (
          <div className="space-y-2 py-4">
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-3/4 animate-pulse" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-5/6 animate-pulse" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2 animate-pulse" />
          </div>
        ) : (
          <textarea
            value={reply}
            onChange={e => setReply(e.target.value)}
            rows={6}
            placeholder="AI reply will appear here..."
            className="w-full bg-transparent text-xs sm:text-sm text-[#1E293B] dark:text-[#F8FAFC] leading-relaxed resize-none outline-none placeholder-[#7B8497]"
          />
        )}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31] flex-wrap gap-2">
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleModify('improve')}
            className="px-2 py-1 rounded text-[11px] font-medium text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white flex items-center gap-1 hover:bg-[#E5EAF2]/50"
          >
            <TrendingUp className="w-3 h-3" /> Improve
          </button>
          <button
            onClick={() => handleModify('shorten')}
            className="px-2 py-1 rounded text-[11px] font-medium text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white flex items-center gap-1 hover:bg-[#E5EAF2]/50"
          >
            <ShrinkIcon className="w-3 h-3" /> Shorten
          </button>
          <button
            onClick={() => handleModify('expand')}
            className="px-2 py-1 rounded text-[11px] font-medium text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white flex items-center gap-1 hover:bg-[#E5EAF2]/50"
          >
            <Expand className="w-3 h-3" /> Expand
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => toast.success('Draft saved')}
            className="btn-secondary text-xs py-1.5 px-3"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Draft</span>
          </button>

          <button
            onClick={handleSend}
            className={`btn-primary text-xs py-1.5 px-4 ${
              sent ? 'bg-emerald-600 hover:bg-emerald-700' : ''
            }`}
          >
            {sent ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Sent!</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Send Reply</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main EmailDetail component ──────────────────────────────
const TABS = [
  { id: 'ai_reply',    label: 'AI Reply',    icon: Sparkles },
  { id: 'summary',     label: 'Summary',     icon: Lightbulb },
  { id: 'thread',      label: 'Thread',      icon: MessageSquare },
  { id: 'attachments', label: 'Attachments', icon: Paperclip },
];

export default function EmailDetail({ onBack }) {
  const { selectedEmail, toggleStar, activePanel, setActivePanel, addTask } = useApp();
  const [showFullBody, setShowFullBody] = useState(false);

  if (!selectedEmail) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-center bg-white dark:bg-[#1E293B]">
        <div>
          <div className="w-12 h-12 rounded-xl bg-[#F5F7FC] dark:bg-slate-800 flex items-center justify-center mx-auto mb-3 text-[#7B8497]">
            <MessageSquare className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-[#1E293B] dark:text-white">Select an email to view</p>
          <p className="text-xs text-[#7B8497] mt-1">Choose any message from the list on the left</p>
        </div>
      </div>
    );
  }

  const email = selectedEmail;

  const handleQuickAddTask = () => {
    addTask({
      title: `Follow up on "${email.subject}"`,
      dueDate: 'Tomorrow',
      priority: 'high',
      emailId: email.id,
    });
    toast.success('Task created from email');
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#1E293B] overflow-hidden">
      {/* ── Email Action Toolbar & Header ── */}
      <div className="px-5 py-3.5 border-b border-[#E5EAF2] dark:border-[#334155] flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          {onBack && (
            <button
              onClick={onBack}
              className="md:hidden p-1.5 -ml-1 rounded-lg text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
              title="Back to inbox list"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}
          <h2 className="text-sm sm:text-base font-bold text-[#1E293B] dark:text-white truncate">
            {email.subject}
          </h2>
          <CategoryBadge category={email.category} />
          {email.requiresReply && (
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD]">
              Needs Reply
            </span>
          )}
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1 shrink-0 text-[#7B8497] dark:text-[#94A3B8]">
          <button
            onClick={() => toggleStar(email.id)}
            className="p-1.5 rounded-lg hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
            title="Star email"
          >
            <Star
              className={`w-4 h-4 ${
                email.isStarred ? 'text-amber-400 fill-amber-400' : ''
              }`}
            />
          </button>
          <button
            onClick={() => setActivePanel('ai_reply')}
            className="p-1.5 rounded-lg hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
            title="Reply"
          >
            <Reply className="w-4 h-4" />
          </button>
          <button
            onClick={() => toast.success('Email archived')}
            className="p-1.5 rounded-lg hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
            title="Archive"
          >
            <Archive className="w-4 h-4" />
          </button>
          <button
            onClick={() => toast.success('Email moved to trash')}
            className="p-1.5 rounded-lg hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Sender info bar ── */}
      <div className="px-5 py-3 border-b border-[#E5EAF2] dark:border-[#334155] flex items-center justify-between gap-3 bg-[#FBFDFF] dark:bg-[#131E31]/50">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar name={email.from.name} size="md" />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs sm:text-sm font-bold text-[#1E293B] dark:text-white">
                {email.from.name}
              </span>
              <span className="text-xs text-[#7B8497]">&lt;{email.from.email}&gt;</span>
            </div>
            <p className="text-[11px] text-[#7B8497] mt-0.5">
              to me • {email.date} at {email.time}
            </p>
          </div>
        </div>

        <button
          onClick={handleQuickAddTask}
          className="btn-secondary text-xs py-1 px-2.5 hidden sm:flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5 text-[#4169E1]" />
          <span>Add Task</span>
        </button>
      </div>

      {/* ── Main Layout: Email content + Contextual AI suggestions on right ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left / Center: Body + AI Reply Tabs */}
        <div className="flex-1 flex flex-col overflow-y-auto p-5 space-y-5">
          {/* Email Body text */}
          <div className="card-white p-4">
            <p className="text-xs sm:text-sm text-[#1E293B] dark:text-[#E2E8F0] leading-relaxed whitespace-pre-line font-normal">
              {showFullBody
                ? email.body
                : email.body.slice(0, 320) + (email.body.length > 320 ? '...' : '')}
            </p>
            {email.body.length > 320 && (
              <button
                onClick={() => setShowFullBody(prev => !prev)}
                className="mt-3 text-xs font-semibold text-[#4169E1] hover:underline"
              >
                {showFullBody ? 'Show less' : 'Read more'}
              </button>
            )}
          </div>

          {/* Tab selector for AI actions */}
          <div>
            <div className="flex items-center gap-1 border-b border-[#E5EAF2] dark:border-[#334155] mb-3">
              {TABS.map(tab => {
                const Icon = tab.icon;
                const isActive = activePanel === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActivePanel(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                      isActive
                        ? 'border-[#4169E1] text-[#4169E1] dark:text-[#93C5FD] font-semibold'
                        : 'border-transparent text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tab contents */}
            <div>
              {activePanel === 'ai_reply' && <AIReplyPanel email={email} />}

              {activePanel === 'summary' && (
                <div className="card-white p-4 space-y-2">
                  <h4 className="text-xs font-bold text-[#1E293B] dark:text-white">AI Executive Summary</h4>
                  <p className="text-xs text-[#475569] dark:text-[#CBD5E1] leading-relaxed">
                    {email.aiAnalysis?.keyPoints?.join('. ') || 'No summary available.'}
                  </p>
                </div>
              )}

              {activePanel === 'thread' && (
                <div className="card-white p-4 space-y-3">
                  <h4 className="text-xs font-bold text-[#1E293B] dark:text-white">Thread Activity</h4>
                  <div className="flex items-center gap-3 text-xs text-[#7B8497]">
                    <GitBranch className="w-4 h-4 text-[#4169E1]" />
                    <span>Single email inquiry thread. No prior exchange found.</span>
                  </div>
                </div>
              )}

              {activePanel === 'attachments' && (
                <div className="card-white p-6 text-center text-xs text-[#7B8497]">
                  No attachments associated with this email.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Contextual AI suggestions when space permits */}
        <div className="w-64 lg:w-72 shrink-0 border-l border-[#E5EAF2] dark:border-[#334155] p-4 space-y-4 bg-[#FBFDFF] dark:bg-[#131E31]/40 overflow-y-auto hidden xl:block">
          <AIAnalysisCard analysis={email.aiAnalysis} />

          {/* Quick Context Actions */}
          <div className="card-white p-3.5 space-y-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[#7B8497]">
              Contextual Actions
            </p>
            <button
              onClick={handleQuickAddTask}
              className="w-full text-left p-2 rounded-lg bg-[#F5F7FC] dark:bg-[#0F172A] hover:bg-[#E8EEFF] dark:hover:bg-[#4169E1]/20 transition-colors border border-[#E5EAF2] dark:border-[#334155] text-xs font-medium text-[#1E293B] dark:text-white flex items-center justify-between"
            >
              <span>Add to Tasks</span>
              <Plus className="w-3.5 h-3.5 text-[#4169E1]" />
            </button>
            <button
              onClick={() => {
                setActivePanel('ai_reply');
                toast.success('Generated response ready in reply box');
              }}
              className="w-full text-left p-2 rounded-lg bg-[#F5F7FC] dark:bg-[#0F172A] hover:bg-[#E8EEFF] dark:hover:bg-[#4169E1]/20 transition-colors border border-[#E5EAF2] dark:border-[#334155] text-xs font-medium text-[#1E293B] dark:text-white flex items-center justify-between"
            >
              <span>Draft Quick Reply</span>
              <Sparkles className="w-3.5 h-3.5 text-[#4169E1]" />
            </button>
            <button
              onClick={() => toast.success('Reminder scheduled for 3 days')}
              className="w-full text-left p-2 rounded-lg bg-[#F5F7FC] dark:bg-[#0F172A] hover:bg-[#E8EEFF] dark:hover:bg-[#4169E1]/20 transition-colors border border-[#E5EAF2] dark:border-[#334155] text-xs font-medium text-[#1E293B] dark:text-white flex items-center justify-between"
            >
              <span>Snooze / Reminder</span>
              <Clock className="w-3.5 h-3.5 text-[#4169E1]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
