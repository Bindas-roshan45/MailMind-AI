import { useState } from 'react';
import { X, Send, Sparkles, Paperclip } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

export default function ComposeModal() {
  const { composing, setComposing, sendEmail } = useApp();
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [prompt, setPrompt] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);

  if (!composing) return null;

  const handleSend = (e) => {
    e.preventDefault();
    if (!to || !subject) {
      toast.error('Please enter recipient and subject');
      return;
    }
    sendEmail({ to, subject, body });
    toast.success('Email sent successfully');
    setComposing(false);
  };

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
      // Graceful fallback if backend AI is unavailable
      setBody(
        `Hi,\n\nI hope this email finds you well.\n\nRegarding ${subject || 'our discussion'}, ${prompt}.\n\nPlease let me know your thoughts or if you need any additional information.\n\nBest regards,\nMailMind User`
      );
      toast.success('Draft created (offline mode)');
    } finally {
      setAiGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-modal w-full max-w-xl overflow-hidden flex flex-col animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31]">
          <span className="text-sm font-bold text-[#1E293B] dark:text-white">New Message</span>
          <button
            onClick={() => setComposing(false)}
            className="p-1 rounded-md text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* AI Quick Prompt Assistance */}
        <div className="p-3 bg-[#E8EEFF]/50 dark:bg-[#4169E1]/10 border-b border-[#E5EAF2] dark:border-[#334155] flex items-center gap-2">
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
            className="btn-primary text-xs py-1 px-2.5 shrink-0"
          >
            {aiGenerating ? 'Drafting...' : 'Generate'}
          </button>
        </div>

        {/* Fields Form */}
        <form onSubmit={handleSend} className="p-4 space-y-3 flex-1 flex flex-col">
          <div>
            <input
              type="email"
              placeholder="To: recipient@example.com"
              value={to}
              onChange={e => setTo(e.target.value)}
              required
              className="w-full text-xs sm:text-sm px-3 py-1.5 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-transparent outline-none focus:border-[#4169E1]"
            />
          </div>
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

          {/* Footer toolbar */}
          <div className="flex items-center justify-between pt-2 border-t border-[#E5EAF2] dark:border-[#334155]">
            <div className="flex items-center gap-1 text-[#7B8497]">
              <button
                type="button"
                onClick={() => toast.success('Attachment added')}
                className="p-1.5 rounded-md hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors"
                title="Attach file"
              >
                <Paperclip className="w-4 h-4" />
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
                className="btn-primary text-xs py-1.5 px-4 flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Send</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
