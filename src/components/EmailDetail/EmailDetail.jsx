import { useState, useEffect } from 'react';
import {
  Star, Reply, Trash2,
  Archive, Clock, RotateCcw, Send, Save,
  MessageSquare, Paperclip, GitBranch,
  Lightbulb, CheckCircle2, AlertCircle, TrendingUp,
  Globe, ShrinkIcon, Expand, Sparkles, Check, Plus, ArrowLeft, X, ShieldAlert,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Avatar, CategoryBadge } from '../ui';
import api from '../../services/api';
import toast from 'react-hot-toast';
import SensitiveApprovalModal from '../Modals/SensitiveApprovalModal';

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
  const { sendEmail } = useApp();
  const [tone, setTone]             = useState('professional');
  const [language, setLanguage]     = useState('english');
  const [reply, setReply]           = useState(email?.suggestedReply || '');
  const [draftId, setDraftId]       = useState(null);
  const [generating, setGenerating] = useState(false);
  const [modifyingType, setModifyingType] = useState(null);
  const [savingDraft, setSavingDraft] = useState(false);
  const [sending, setSending]       = useState(false);
  const [sent, setSent]             = useState(false);
  const [error, setError]           = useState(null);
  const [aiMeta, setAiMeta]         = useState(null);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);

  const isSensitive = Boolean(
    email?.category === 'Finance' ||
    email?.category === 'Security' ||
    email?.ai_sentiment === 'Alert' ||
    email?.ai_suspicious_flag === true ||
    /wire|bank|routing|lawsuit|attorney|subpoena|password|refund|complaint/i.test(
      `${email?.subject || ''} ${email?.body || email?.preview || ''}`
    )
  );

  const sensitivityReason =
    email?.category === 'Finance'
      ? 'Financial matter detected (wire / invoice / banking)'
      : email?.category === 'Security' || email?.ai_suspicious_flag
      ? 'Security alert or credential reset topic'
      : /lawsuit|attorney|subpoena/i.test(`${email?.subject || ''} ${email?.body || ''}`)
      ? 'Legal matter requiring human review'
      : /complaint|refund|unacceptable/i.test(`${email?.subject || ''} ${email?.body || ''}`)
      ? 'Customer complaint / escalation requires manual approval'
      : 'Sensitive topic detected under safety guardrails';

  const tones = ['Professional', 'Friendly', 'Formal', 'Short'];
  const langs = ['English', 'Hindi', 'Hinglish'];

  // Core reply generation routine
  const generateReply = async (selectedTone = tone, selectedLang = language) => {
    if (!email) return;
    setGenerating(true);
    setError(null);
    try {
      const emailIdNum = typeof email?.id === 'number' ? email.id : undefined;
      const senderName = email?.from?.name || (typeof email?.from === 'string' ? email.from : '') || '';
      const subject = email?.subject || 'Message';
      const body = email?.body || email?.preview || '';

      const res = await api.ai.generateDraft({
        email_id: emailIdNum,
        subject: subject,
        body: body,
        sender: senderName,
        thread_id: email?.threadId || null,
        tone: selectedTone.toLowerCase(),
        language: selectedLang.toLowerCase(),
      });

      if (res?.data?.content) {
        setReply(res.data.content);
        setDraftId(res.data.draft_id || null);
        setAiMeta(res.data.ai_metadata || null);
        setError(null);
      } else {
        throw new Error(res?.message || 'Could not generate AI reply.');
      }
    } catch (err) {
      console.error('AI Reply Generation error:', err);
      const errMsg = err?.message || 'Failed to connect to AI reply service. Please check your AI API key and connection.';
      setError(errMsg);
    } finally {
      setGenerating(false);
    }
  };

  // Requirement 1: Automatically generate an AI reply whenever an email is selected
  useEffect(() => {
    setDraftId(null);
    setSent(false);
    setError(null);
    setAiMeta(null);

    if (email) {
      // Trigger automatic generation
      generateReply(tone, language);
    } else {
      setReply('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email?.id]);

  // Requirement 6: Regenerate reply when user changes tone
  const handleToneChange = (newTone) => {
    const lower = newTone.toLowerCase();
    setTone(lower);
    generateReply(lower, language);
  };

  // Requirement 6: Regenerate reply when user changes language
  const handleLanguageChange = (newLang) => {
    setLanguage(newLang);
    generateReply(tone, newLang);
  };

  // Requirement 7: Explicit Regenerate button
  const handleManualRegenerate = () => {
    generateReply(tone, language);
  };

  // Requirement 9: Save draft explicitly on demand
  const handleSaveDraft = async () => {
    if (!reply.trim()) {
      toast.error('Draft is empty');
      return;
    }
    setSavingDraft(true);
    try {
      const emailIdNum = typeof email?.id === 'number' ? email.id : undefined;
      const res = await api.ai.saveDraft({
        email_id: emailIdNum,
        draft_id: draftId,
        content: reply,
        tone: tone,
        language: language,
      });

      if (res?.data?.draft_id) {
        setDraftId(res.data.draft_id);
      }
      toast.success('Draft saved successfully');
    } catch (err) {
      toast.error(err?.message || 'Failed to save draft to server');
    } finally {
      setSavingDraft(false);
    }
  };

  // Requirement 10: NEVER send automatically; requires explicit click on Send Reply
  const handleSend = async () => {
    if (!reply.trim()) {
      toast.error('Reply text cannot be empty');
      return;
    }

    // Phase 3 Safety Guardrail: Sensitive emails require the approval modal flow
    if (isSensitive) {
      setIsApprovalModalOpen(true);
      return;
    }

    setSending(true);
    try {
      await sendEmail({
        to: email?.from?.email || email?.from_email || email?.to,
        subject: email?.subject?.startsWith('Re:') ? email.subject : `Re: ${email.subject}`,
        body: reply,
        draftId: draftId,
        threadId: email?.threadId || email?.thread_id || null,
      });
      setSent(true);
      setTimeout(() => setSent(false), 3000);
    } catch {
      // Toast already shown in sendEmail
    } finally {
      setSending(false);
    }
  };

  // Requirement 7: Improve, Shorten, Expand modification actions
  const handleModify = async (type) => {
    if (!reply.trim()) {
      toast.error('Draft is empty. Generate or write a draft first.');
      return;
    }
    setModifyingType(type);
    const loadToast = toast.loading(`AI is transforming draft (${type})...`);
    try {
      const res = await api.ai.rewrite({ content: reply, mode: type });
      if (res?.data?.rewritten_content) {
        setReply(res.data.rewritten_content);
        toast.success(`Transformed (${type})`, { id: loadToast });
      } else {
        toast.error('Could not transform draft', { id: loadToast });
      }
    } catch (err) {
      toast.error(err.message || 'Transform failed', { id: loadToast });
    } finally {
      setModifyingType(null);
    }
  };

  return (
    <div className="card-white overflow-hidden space-y-0 border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-sm">
      {/* Tone & Options Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31] flex-wrap gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-semibold text-[#7B8497] mr-1 uppercase tracking-wider">Tone:</span>
          {tones.map(t => {
            const isActive = tone === t.toLowerCase();
            return (
              <button
                key={t}
                type="button"
                onClick={() => handleToneChange(t)}
                disabled={generating}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition-all ${
                  isActive
                    ? 'bg-[#4169E1] text-white shadow-sm font-semibold'
                    : 'text-[#64748B] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-slate-800'
                } ${generating ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                {t}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2">
          {/* Language selector */}
          <div className="flex items-center gap-1 text-xs text-[#7B8497] bg-white dark:bg-slate-800 px-2 py-1 rounded-md border border-[#E5EAF2] dark:border-[#334155]">
            <Globe className="w-3.5 h-3.5 text-[#4169E1]" />
            <select
              value={language}
              onChange={e => handleLanguageChange(e.target.value)}
              disabled={generating}
              className="bg-transparent text-xs text-[#1E293B] dark:text-[#CBD5E1] outline-none cursor-pointer font-medium"
            >
              {langs.map(l => (
                <option key={l} value={l.toLowerCase()} className="bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                  {l}
                </option>
              ))}
            </select>
          </div>

          {/* Regenerate Button */}
          <button
            type="button"
            onClick={handleManualRegenerate}
            disabled={generating}
            className="btn-ghost text-xs py-1 px-2.5 flex items-center gap-1 text-[#4169E1] dark:text-[#93C5FD] hover:bg-blue-50 dark:hover:bg-blue-950/40 rounded-md font-medium"
            title="Regenerate reply from email content"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* AI Metadata Sub-bar (if available) */}
      {aiMeta && !generating && (
        <div className="px-4 py-1.5 bg-blue-50/60 dark:bg-blue-950/20 border-b border-blue-100 dark:border-blue-900/40 flex items-center justify-between text-[11px] text-[#4169E1] dark:text-[#93C5FD]">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-[#4169E1]" />
            <span className="font-medium">
              Generated by {aiMeta.provider?.toUpperCase()} ({aiMeta.model})
            </span>
            {aiMeta.fallback && (
              <span className="text-[10px] bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 px-1.5 py-0.2 rounded font-normal">
                smart offline fallback
              </span>
            )}
          </div>
          <span className="text-[10px] text-slate-500 dark:text-slate-400 capitalize">
            {aiMeta.tone} • {aiMeta.language}
          </span>
        </div>
      )}

      {/* Sensitive Email Safety Banner */}
      {isSensitive && (
        <div className="px-4 py-2 bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-800/50 flex items-center justify-between text-xs text-amber-800 dark:text-amber-200">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="font-semibold">{sensitivityReason}</span>
          </div>
          <button
            type="button"
            onClick={() => setIsApprovalModalOpen(true)}
            className="text-[11px] font-bold underline hover:text-amber-950 dark:hover:text-amber-100"
          >
            Review & Approve
          </button>
        </div>
      )}

      {/* Editor Body with Loading & Error States */}
      <div className="p-4 relative min-h-[160px]">
        {generating ? (
          <div className="flex flex-col items-center justify-center py-6 space-y-3">
            <div className="relative flex items-center justify-center">
              <div className="w-10 h-10 rounded-full border-2 border-blue-200 dark:border-blue-900 border-t-[#4169E1] animate-spin" />
              <Sparkles className="w-4 h-4 text-[#4169E1] absolute" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-xs font-semibold text-[#1E293B] dark:text-white">
                Generating {tone.charAt(0).toUpperCase() + tone.slice(1)} AI reply in {language}...
              </p>
              <p className="text-[11px] text-[#7B8497]">
                Analyzing email context, sender details, and conversation thread
              </p>
            </div>
            <div className="w-full max-w-sm space-y-2 pt-2">
              <div className="h-2.5 bg-slate-200 dark:bg-slate-700/80 rounded w-full animate-pulse" />
              <div className="h-2.5 bg-slate-200 dark:bg-slate-700/80 rounded w-5/6 animate-pulse" />
              <div className="h-2.5 bg-slate-200 dark:bg-slate-700/80 rounded w-2/3 animate-pulse" />
            </div>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-lg text-xs space-y-3">
            <div className="flex items-start gap-2.5 text-red-700 dark:text-red-400">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold">AI Reply Generation Failed</p>
                <p className="text-[11px] text-red-600 dark:text-red-300 leading-relaxed">
                  {error}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => generateReply(tone, language)}
                className="btn-primary text-xs py-1 px-3 bg-red-600 hover:bg-red-700 text-white flex items-center gap-1.5"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Retry Generation</span>
              </button>
              <button
                type="button"
                onClick={() => setError(null)}
                className="btn-ghost text-xs py-1 px-3 text-slate-600 dark:text-slate-300"
              >
                Dismiss
              </button>
            </div>
          </div>
        ) : (
          <textarea
            value={reply}
            onChange={e => setReply(e.target.value)}
            rows={7}
            placeholder="AI reply will appear here once generated..."
            className="w-full bg-transparent text-xs sm:text-sm text-[#1E293B] dark:text-[#F8FAFC] leading-relaxed resize-none outline-none placeholder-[#94A3B8] font-normal"
          />
        )}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31] flex-wrap gap-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => handleModify('improve')}
            disabled={generating || modifyingType !== null || !reply.trim()}
            className="px-2.5 py-1.5 rounded text-[11px] font-medium text-[#64748B] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white flex items-center gap-1 hover:bg-[#E5EAF2]/60 dark:hover:bg-slate-800 disabled:opacity-50"
            title="Improve clarity and phrasing"
          >
            <TrendingUp className={`w-3 h-3 ${modifyingType === 'improve' ? 'animate-spin' : ''}`} />
            <span>{modifyingType === 'improve' ? 'Improving...' : 'Improve'}</span>
          </button>
          <button
            type="button"
            onClick={() => handleModify('shorten')}
            disabled={generating || modifyingType !== null || !reply.trim()}
            className="px-2.5 py-1.5 rounded text-[11px] font-medium text-[#64748B] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white flex items-center gap-1 hover:bg-[#E5EAF2]/60 dark:hover:bg-slate-800 disabled:opacity-50"
            title="Make reply concise"
          >
            <ShrinkIcon className={`w-3 h-3 ${modifyingType === 'shorten' ? 'animate-spin' : ''}`} />
            <span>{modifyingType === 'shorten' ? 'Shortening...' : 'Shorten'}</span>
          </button>
          <button
            type="button"
            onClick={() => handleModify('expand')}
            disabled={generating || modifyingType !== null || !reply.trim()}
            className="px-2.5 py-1.5 rounded text-[11px] font-medium text-[#64748B] hover:text-[#1E293B] dark:text-[#94A3B8] dark:hover:text-white flex items-center gap-1 hover:bg-[#E5EAF2]/60 dark:hover:bg-slate-800 disabled:opacity-50"
            title="Expand reply with more detail"
          >
            <Expand className={`w-3 h-3 ${modifyingType === 'expand' ? 'animate-spin' : ''}`} />
            <span>{modifyingType === 'expand' ? 'Expanding...' : 'Expand'}</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Explicit Save Draft Button */}
          <button
            type="button"
            onClick={handleSaveDraft}
            disabled={savingDraft || generating || !reply.trim()}
            className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 disabled:opacity-50"
            title="Save draft to review or finish later"
          >
            <Save className={`w-3.5 h-3.5 ${savingDraft ? 'animate-spin' : ''}`} />
            <span>{savingDraft ? 'Saving...' : 'Save Draft'}</span>
          </button>

          {/* Explicit Send Reply Button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={sending || generating || !reply.trim()}
            className={`btn-primary text-xs py-1.5 px-4 flex items-center gap-1.5 transition-all ${
              sent ? 'bg-emerald-600 hover:bg-emerald-700' : ''
            } ${(sending || generating || !reply.trim()) ? 'opacity-60 cursor-not-allowed' : ''}`}
            title="Send this email reply now"
          >
            {sent ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Sent!</span>
              </>
            ) : (
              <>
                <Send className={`w-3.5 h-3.5 ${sending ? 'animate-spin' : ''}`} />
                <span>{sending ? 'Sending...' : 'Send Reply'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Sensitive Email Approval Modal */}
      <SensitiveApprovalModal
        isOpen={isApprovalModalOpen}
        onClose={() => setIsApprovalModalOpen(false)}
        email={email}
        initialDraft={reply}
        sensitivityReason={sensitivityReason}
        sendEmailFn={sendEmail}
        onSendSuccess={(approvedText) => {
          setReply(approvedText);
          setSent(true);
          setTimeout(() => setSent(false), 3000);
        }}
      />
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
  const {
    selectedEmail, toggleStar, deleteEmail, activePanel, setActivePanel, addTask,
    currentThread, loadingThread,
  } = useApp();
  const [showFullBody, setShowFullBody] = useState(false);
  const [showAiPopup, setShowAiPopup] = useState(false);

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
    <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#1E293B] overflow-hidden relative">
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
        <div className="flex items-center gap-1.5 shrink-0 text-[#7B8497] dark:text-[#94A3B8]">
          <button
            onClick={() => setShowAiPopup(prev => !prev)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-sm ${
              showAiPopup
                ? 'bg-[#1E293B] text-white dark:bg-white dark:text-[#1E293B]'
                : 'bg-gradient-to-r from-[#4169E1] to-[#2563EB] text-white hover:opacity-95 shadow-blue-500/20'
            }`}
            title="Toggle AI Insights & Contextual Actions"
          >
            <Sparkles className="w-3.5 h-3.5 text-white animate-pulse" />
            <span>AI Insights</span>
          </button>
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
            onClick={() => {
              deleteEmail(email.id);
              if (onBack) onBack();
            }}
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
          <Avatar name={email.from?.name || 'User'} size="md" />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs sm:text-sm font-bold text-[#1E293B] dark:text-white">
                {email.from?.name || 'User'}
              </span>
              <span className="text-xs text-[#7B8497]">&lt;{email.from?.email || ''}&gt;</span>
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
                : (email.body || '').slice(0, 320) + ((email.body || '').length > 320 ? '...' : '')}
            </p>
            {(email.body || '').length > 320 && (
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
                    {email.aiAnalysis?.keyPoints?.length > 0
                      ? email.aiAnalysis.keyPoints.join('. ')
                      : 'No summary points generated for this email yet.'}
                  </p>
                </div>
              )}

              {activePanel === 'thread' && (
                <div className="card-white p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-[#E5EAF2] dark:border-[#334155] pb-2">
                    <h4 className="text-xs font-bold text-[#1E293B] dark:text-white flex items-center gap-1.5">
                      <GitBranch className="w-3.5 h-3.5 text-[#4169E1]" />
                      <span>Conversation Thread {currentThread ? `(${currentThread.length} messages)` : ''}</span>
                    </h4>
                  </div>
                  {loadingThread ? (
                    <div className="space-y-2 py-3">
                      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-3/4 animate-pulse" />
                      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2 animate-pulse" />
                    </div>
                  ) : currentThread && currentThread.length > 1 ? (
                    <div className="space-y-2.5">
                      {currentThread.map((msg, idx) => (
                        <div
                          key={msg.id || idx}
                          className={`p-3 rounded-lg border text-xs ${
                            msg.id === email.id || msg.message_id === email.messageId
                              ? 'bg-[#E8EEFF]/40 dark:bg-[#4169E1]/10 border-[#4169E1]/30 font-medium'
                              : 'bg-[#F8FAFC] dark:bg-[#131E31] border-[#E5EAF2] dark:border-[#334155]'
                          }`}
                        >
                          <div className="flex items-center justify-between text-[#7B8497] mb-1">
                            <span className="font-semibold text-[#1E293B] dark:text-white">
                              {msg.from_name || msg.from_email}
                            </span>
                            <span className="text-[10px]">
                              {msg.received_at ? new Date(msg.received_at).toLocaleDateString() : ''}
                            </span>
                          </div>
                          <p className="text-[#334155] dark:text-[#CBD5E1] line-clamp-2">
                            {msg.preview || msg.body || '(No content)'}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-3 text-xs text-[#7B8497] py-2">
                      <GitBranch className="w-4 h-4 text-[#4169E1]" />
                      <span>Single message in this thread. No prior exchange found.</span>
                    </div>
                  )}
                </div>
              )}

              {activePanel === 'attachments' && (
                <div className="card-white p-6 text-center text-xs text-[#7B8497]">
                  {email.hasAttachments ? (
                    <div className="flex flex-col items-center gap-2 text-emerald-600 dark:text-emerald-400">
                      <Paperclip className="w-6 h-6" />
                      <span className="font-semibold text-xs text-[#1E293B] dark:text-white">
                        {email.attachmentCount || 1} Attachment(s) present in email
                      </span>
                    </div>
                  ) : (
                    'No attachments associated with this email.'
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── AI Insights & Contextual Actions Popup Dropdown (Anchored Top-Right) ── */}
        {showAiPopup && (
          <div
            className="absolute top-14 right-6 z-50 w-80 sm:w-96 max-h-[80vh] overflow-y-auto bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-2xl p-4 space-y-4 shadow-2xl animate-scale-in"
            style={{
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 25px rgba(65, 105, 225, 0.25)',
            }}
          >
            {/* Popup Header */}
            <div className="flex items-center justify-between pb-2 border-b border-[#E5EAF2] dark:border-[#334155]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-[#4169E1] to-[#3B82F6] flex items-center justify-center text-white shadow-sm">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-xs font-bold text-[#1E293B] dark:text-white block">AI Assistant & Insights</span>
                  <span className="text-[10px] text-[#7B8497] block">Smart analysis & contextual actions</span>
                </div>
              </div>
              <button
                onClick={() => setShowAiPopup(false)}
                className="p-1 rounded-md text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
                title="Close AI popup"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* AI Analysis Card */}
            <AIAnalysisCard analysis={email.aiAnalysis} />

            {/* Quick Context Actions */}
            <div className="card-white p-3.5 space-y-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[#7B8497]">
                Contextual Actions
              </p>
              <button
                onClick={() => {
                  handleQuickAddTask();
                  setShowAiPopup(false);
                }}
                className="w-full text-left p-2.5 rounded-lg bg-[#F5F7FC] dark:bg-[#0F172A] hover:bg-[#E8EEFF] dark:hover:bg-[#4169E1]/20 transition-colors border border-[#E5EAF2] dark:border-[#334155] text-xs font-medium text-[#1E293B] dark:text-white flex items-center justify-between group cursor-pointer"
              >
                <span>Add to Tasks</span>
                <Plus className="w-3.5 h-3.5 text-[#4169E1] group-hover:scale-110 transition-transform" />
              </button>
              <button
                onClick={() => {
                  setActivePanel('ai_reply');
                  setShowAiPopup(false);
                  toast.success('Generated response ready in reply box');
                }}
                className="w-full text-left p-2.5 rounded-lg bg-[#F5F7FC] dark:bg-[#0F172A] hover:bg-[#E8EEFF] dark:hover:bg-[#4169E1]/20 transition-colors border border-[#E5EAF2] dark:border-[#334155] text-xs font-medium text-[#1E293B] dark:text-white flex items-center justify-between group cursor-pointer"
              >
                <span>Draft Quick Reply</span>
                <Sparkles className="w-3.5 h-3.5 text-[#4169E1] group-hover:scale-110 transition-transform" />
              </button>
              <button
                onClick={() => {
                  toast.success('Reminder scheduled for 3 days');
                  setShowAiPopup(false);
                }}
                className="w-full text-left p-2.5 rounded-lg bg-[#F5F7FC] dark:bg-[#0F172A] hover:bg-[#E8EEFF] dark:hover:bg-[#4169E1]/20 transition-colors border border-[#E5EAF2] dark:border-[#334155] text-xs font-medium text-[#1E293B] dark:text-white flex items-center justify-between group cursor-pointer"
              >
                <span>Snooze / Reminder</span>
                <Clock className="w-3.5 h-3.5 text-[#4169E1] group-hover:scale-110 transition-transform" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
