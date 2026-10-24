import { useState, useEffect, useRef } from 'react';
import {
  X, Send, Sparkles, Paperclip,
  Bookmark, Bold, Italic, List, Quote
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

const PRESET_TEMPLATES = [
  {
    name: 'Meeting Follow-up',
    subject: 'Follow-up: Today\'s Discussion & Next Steps',
    body: 'Hi,\n\nThank you for taking the time to meet earlier today. It was great discussing our current priorities.\n\nAs agreed, here are the key next steps:\n1. Review project deliverables\n2. Share updated timeline by Friday\n\nPlease let me know if you have any questions in the meantime.\n\nBest regards,',
  },
  {
    name: 'Inquiry Acknowledgment',
    subject: 'Received: Your Inquiry with MailMind',
    body: 'Hi,\n\nThank you for reaching out! We have received your message and are looking into it. Our team will follow up within 24 hours with complete details.\n\nBest regards,',
  },
  {
    name: 'Schedule Coordination',
    subject: 'Meeting Request / Time Coordination',
    body: 'Hi,\n\nI would love to connect this week to discuss our collaboration. Would you be open for a 20-minute call on Wednesday or Thursday afternoon?\n\nLooking forward to hearing from you.',
  },
  {
    name: 'Status Update',
    subject: 'Weekly Progress & Milestone Update',
    body: 'Hi Team,\n\nHere is a quick snapshot of milestones achieved this week:\n- Core feature implementation completed\n- Quality assurance and test coverage on track\n- Next release planned for next Tuesday\n\nBest,',
  },
];

export default function ComposeModal() {
  const { composing, setComposing, sendEmail } = useApp();

  const [mode, setMode] = useState('new');
  const [to, setTo] = useState('');
  const [cc, setCc] = useState('');
  const [bcc, setBcc] = useState('');
  const [showCcBcc, setShowCcBcc] = useState(false);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [prompt, setPrompt] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [draftId, setDraftId] = useState(null);
  const [savingDraft, setSavingDraft] = useState(false);

  // Attachments
  const [attachments, setAttachments] = useState([]);
  const fileInputRef = useRef(null);

  // Signatures
  const [signatures, setSignatures] = useState([]);
  const [selectedSigId, setSelectedSigId] = useState(null);

  // Undo Send countdown state
  const [undoCountdown, setUndoCountdown] = useState(null);
  const undoTimerRef = useRef(null);

  // Synchronize initial state when modal opens
  useEffect(() => {
    if (!composing) {
      if (undoTimerRef.current) {
        clearInterval(undoTimerRef.current);
        undoTimerRef.current = null;
      }
      setUndoCountdown(null);
      return;
    }

    if (typeof composing === 'object') {
      setMode(composing.mode || 'new');
      setTo(composing.to || '');
      setCc(composing.cc || '');
      setBcc(composing.bcc || '');
      setShowCcBcc(Boolean(composing.cc || composing.bcc));
      setSubject(composing.subject || '');
      setBody(composing.body || '');
      setDraftId(composing.draftId || null);
    } else {
      setMode('new');
      setTo('');
      setCc('');
      setBcc('');
      setShowCcBcc(false);
      setSubject('');
      setBody('');
      setDraftId(null);
    }

    setAttachments([]);
    setPrompt('');
    setUndoCountdown(null);

    // Fetch user signatures to auto-select default
    api.signatures.list()
      .then(res => {
        if (res?.success && res.data) {
          setSignatures(res.data);
          const isReply = typeof composing === 'object' && (composing.mode === 'reply' || composing.mode === 'reply_all');
          const defaultSig = isReply
            ? res.data.find(s => s.is_default_reply) || res.data.find(s => s.is_default_new)
            : res.data.find(s => s.is_default_new);
          if (defaultSig) {
            setSelectedSigId(defaultSig.id);
          }
        }
      })
      .catch(() => {});
  }, [composing]);

  if (!composing) return null;

  // File attachments handler with 25MB validation
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB
    const validFiles = [];

    for (const file of files) {
      if (file.size > MAX_FILE_SIZE) {
        toast.error(`"${file.name}" exceeds 25MB attachment limit`);
        continue;
      }
      validFiles.push(file);
    }

    validFiles.forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64Data = reader.result.split(',')[1];
        setAttachments(prev => [
          ...prev,
          {
            name: file.name,
            size: file.size,
            type: file.type || 'application/octet-stream',
            content: base64Data,
          },
        ]);
      };
      reader.readAsDataURL(file);
    });

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Template insertion
  const applyTemplate = (tpl) => {
    if (!subject && tpl.subject) setSubject(tpl.subject);
    setBody(prev => (prev ? `${prev}\n\n${tpl.body}` : tpl.body));
    toast.success(`Inserted "${tpl.name}" template`);
  };

  // AI draft assistant
  const handleAiDraft = async () => {
    if (!prompt.trim() && !subject.trim()) {
      toast.error('Enter a prompt or subject for AI drafting');
      return;
    }
    setAiGenerating(true);
    try {
      const res = await api.ai.generateDraft({
        subject: subject || 'New Message',
        body: body,
        prompt: prompt.trim(),
        tone: 'professional',
      });
      if (res?.data?.content) {
        setBody(res.data.content);
        toast.success('AI drafted your email!');
      } else {
        throw new Error('No draft returned');
      }
      setPrompt('');
    } catch {
      setBody(
        `Hi,\n\nI hope this email finds you well.\n\nRegarding ${subject || 'our discussion'}, ${prompt}.\n\nPlease let me know your thoughts or if you need any additional information.\n\nBest regards,\nMailMind User`
      );
      toast.success('Draft created (offline mode)');
    } finally {
      setAiGenerating(false);
    }
  };

  // Save draft
  const handleSaveDraft = async () => {
    setSavingDraft(true);
    try {
      const res = await api.emails.saveDraft({
        id: draftId,
        to,
        subject: subject || 'Untitled Draft',
        body,
        thread_id: composing?.threadId || null,
      });
      if (res?.success) {
        setDraftId(res.data.id);
        toast.success('Draft saved');
      }
    } catch {
      toast.error('Failed to save draft');
    } finally {
      setSavingDraft(false);
    }
  };

  // Formatting helpers
  const applyFormat = (syntax) => {
    setBody(prev => `${prev}\n${syntax} `);
  };

  // Signature attachment
  const getSelectedSignatureText = () => {
    if (!selectedSigId) return '';
    const sig = signatures.find(s => s.id === Number(selectedSigId));
    if (!sig) return '';
    const lines = [sig.sign_off || 'Best regards,', sig.name];
    if (sig.designation) lines.push(sig.designation);
    if (sig.company) lines.push(sig.company);
    if (sig.phone) lines.push(`Tel: ${sig.phone}`);
    return `\n\n${lines.join('\n')}`;
  };

  // Trigger Send with Undo Send delay (5 seconds)
  const initiateSend = (e) => {
    e.preventDefault();
    if (!to || !subject) {
      toast.error('Please enter recipient and subject');
      return;
    }

    // Start 5-second countdown
    let secondsLeft = 5;
    setUndoCountdown(secondsLeft);

    undoTimerRef.current = setInterval(() => {
      secondsLeft -= 1;
      if (secondsLeft <= 0) {
        clearInterval(undoTimerRef.current);
        undoTimerRef.current = null;
        executeFinalSend();
      } else {
        setUndoCountdown(secondsLeft);
      }
    }, 1000);
  };

  // Cancel Undo Send
  const cancelUndoSend = () => {
    if (undoTimerRef.current) {
      clearInterval(undoTimerRef.current);
      undoTimerRef.current = null;
    }
    setUndoCountdown(null);
    toast('Send canceled. Draft restored.', { icon: '↩️' });
  };

  // Final Dispatch after Undo window expires
  const executeFinalSend = async () => {
    setUndoCountdown(null);
    const finalBody = body + getSelectedSignatureText();
    const formattedAttachments = attachments.map(a => ({
      filename: a.name,
      content: a.content,
      content_type: a.type,
    }));

    try {
      await sendEmail({
        to,
        subject,
        body: finalBody,
        cc: cc || undefined,
        bcc: bcc || undefined,
        draftId: draftId,
        threadId: composing?.threadId || undefined,
        inReplyTo: composing?.inReplyTo || undefined,
        attachments: formattedAttachments.length ? formattedAttachments : undefined,
      });
      setComposing(false);
    } catch {
      // Error handled in sendEmail
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col animate-slide-up max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31]">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#1E293B] dark:text-white capitalize">
              {mode === 'reply' ? 'Reply' : mode === 'reply_all' ? 'Reply All' : mode === 'forward' ? 'Forward' : 'New Message'}
            </span>
            {draftId && (
              <span className="text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 px-2 py-0.5 rounded font-mono">
                Draft #{draftId}
              </span>
            )}
          </div>
          <button
            onClick={() => setComposing(false)}
            className="p-1 rounded-md text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Undo Send Countdown Banner */}
        {undoCountdown !== null && (
          <div className="bg-amber-500 text-white px-4 py-2 flex items-center justify-between text-xs animate-pulse">
            <div className="flex items-center gap-2">
              <span className="font-semibold">Sending in {undoCountdown}s...</span>
              <span className="text-amber-100 hidden sm:inline">You can undo or adjust your email</span>
            </div>
            <button
              type="button"
              onClick={cancelUndoSend}
              className="bg-white text-amber-700 font-bold px-3 py-1 rounded shadow hover:bg-amber-50 transition-colors"
            >
              Undo Send
            </button>
          </div>
        )}

        {/* AI Quick Prompt Assistance */}
        <div className="p-2.5 bg-[#E8EEFF]/40 dark:bg-[#4169E1]/10 border-b border-[#E5EAF2] dark:border-[#334155] flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#4169E1] shrink-0" />
          <input
            type="text"
            placeholder="Ask AI to write: e.g. Request project timeline update..."
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAiDraft(); } }}
            className="flex-1 bg-white dark:bg-[#0F172A] border border-[#E5EAF2] dark:border-[#334155] rounded-lg px-2.5 py-1 text-xs outline-none focus:border-[#4169E1]"
          />
          <button
            onClick={handleAiDraft}
            disabled={aiGenerating}
            className="btn-primary text-xs py-1 px-3 shrink-0"
          >
            {aiGenerating ? 'Drafting...' : 'Generate'}
          </button>
        </div>

        {/* Fields Form */}
        <form onSubmit={initiateSend} className="p-4 space-y-2.5 flex-1 flex flex-col overflow-y-auto">
          {/* Recipient & CC/BCC Toggle */}
          <div className="flex items-center gap-2">
            <input
              type="email"
              placeholder="To: recipient@example.com"
              value={to}
              onChange={e => setTo(e.target.value)}
              required
              className="flex-1 text-xs sm:text-sm px-3 py-1.5 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-transparent outline-none focus:border-[#4169E1]"
            />
            <button
              type="button"
              onClick={() => setShowCcBcc(prev => !prev)}
              className="text-xs text-[#4169E1] hover:underline font-medium px-1"
            >
              {showCcBcc ? 'Hide Cc/Bcc' : 'Cc / Bcc'}
            </button>
          </div>

          {/* Expanded CC / BCC fields */}
          {showCcBcc && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 animate-fade-in">
              <input
                type="text"
                placeholder="Cc: colleague@example.com"
                value={cc}
                onChange={e => setCc(e.target.value)}
                className="text-xs px-3 py-1.5 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-transparent outline-none focus:border-[#4169E1]"
              />
              <input
                type="text"
                placeholder="Bcc: archive@example.com"
                value={bcc}
                onChange={e => setBcc(e.target.value)}
                className="text-xs px-3 py-1.5 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-transparent outline-none focus:border-[#4169E1]"
              />
            </div>
          )}

          {/* Subject Field */}
          <div>
            <input
              type="text"
              placeholder="Subject"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              required
              className="w-full text-xs sm:text-sm px-3 py-1.5 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-transparent outline-none focus:border-[#4169E1]"
            />
          </div>

          {/* Rich text formatting & template shortcuts toolbar */}
          <div className="flex items-center justify-between border-b border-[#E5EAF2] dark:border-[#334155] pb-1.5 text-xs text-[#7B8497] flex-wrap gap-2">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => applyFormat('**Bold text**')}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Bold"
              >
                <Bold className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => applyFormat('*Italic text*')}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Italic"
              >
                <Italic className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => applyFormat('- ')}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Bullet List"
              >
                <List className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => applyFormat('> ')}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Quote"
              >
                <Quote className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Template selector */}
            <div className="flex items-center gap-1">
              <span className="text-[11px] text-[#7B8497]">Template:</span>
              <select
                onChange={e => {
                  const tpl = PRESET_TEMPLATES.find(p => p.name === e.target.value);
                  if (tpl) applyTemplate(tpl);
                  e.target.value = '';
                }}
                defaultValue=""
                className="text-xs bg-transparent border border-[#E5EAF2] dark:border-[#334155] rounded px-2 py-0.5 outline-none cursor-pointer text-[#1E293B] dark:text-slate-200"
              >
                <option value="" disabled>Select template...</option>
                {PRESET_TEMPLATES.map(p => (
                  <option key={p.name} value={p.name} className="dark:bg-[#1E293B]">
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Email Body Editor */}
          <div className="flex-1 min-h-[160px]">
            <textarea
              placeholder="Write your email here..."
              rows={8}
              value={body}
              onChange={e => setBody(e.target.value)}
              required
              className="w-full h-full text-xs sm:text-sm p-3 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-transparent outline-none focus:border-[#4169E1] resize-none leading-relaxed"
            />
          </div>

          {/* Attachment Chips Display */}
          {attachments.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap pt-1">
              {attachments.map((att, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/60 text-xs text-blue-700 dark:text-blue-300"
                >
                  <Paperclip className="w-3 h-3 shrink-0" />
                  <span className="max-w-[150px] truncate font-medium">{att.name}</span>
                  <span className="text-[10px] text-blue-500">({formatFileSize(att.size)})</span>
                  <button
                    type="button"
                    onClick={() => removeAttachment(i)}
                    className="hover:text-red-500 transition-colors ml-1"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Signature Selection Bar */}
          {signatures.length > 0 && (
            <div className="flex items-center justify-between text-xs text-[#7B8497] pt-1 border-t border-[#E5EAF2] dark:border-[#334155]">
              <span className="text-[11px]">Append Signature:</span>
              <select
                value={selectedSigId || ''}
                onChange={e => setSelectedSigId(e.target.value ? Number(e.target.value) : null)}
                className="bg-transparent border border-[#E5EAF2] dark:border-[#334155] rounded px-2 py-0.5 text-xs outline-none text-[#1E293B] dark:text-slate-200 cursor-pointer"
              >
                <option value="" className="dark:bg-[#1E293B]">None</option>
                {signatures.map(s => (
                  <option key={s.id} value={s.id} className="dark:bg-[#1E293B]">
                    {s.name} ({s.sign_off || 'Regards'})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            multiple
            className="hidden"
          />

          {/* Footer toolbar */}
          <div className="flex items-center justify-between pt-2 border-t border-[#E5EAF2] dark:border-[#334155]">
            <div className="flex items-center gap-1 text-[#7B8497]">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-1.5 rounded-md hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
                title="Attach file (<25MB)"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={savingDraft}
                className="text-xs px-2.5 py-1 rounded text-[#64748B] hover:text-[#1E293B] dark:hover:text-white flex items-center gap-1 hover:bg-[#F5F7FC] dark:hover:bg-[#28384E]"
                title="Save draft to drafts folder"
              >
                <Bookmark className="w-3.5 h-3.5" />
                <span>{savingDraft ? 'Saving...' : 'Save Draft'}</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setComposing(false)}
                className="btn-secondary text-xs py-1.5 px-3"
              >
                Discard
              </button>
              <button
                type="submit"
                disabled={undoCountdown !== null}
                className="btn-primary text-xs py-1.5 px-4 flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{undoCountdown !== null ? 'Sending...' : 'Send'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
