import React, { useState, useEffect } from 'react';
import {
  PenTool,
  Plus,
  Trash2,
  Eye,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../services/api';

export default function SignatureSettings() {
  const [signatures, setSignatures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  // Form state
  const [name, setName] = useState('Work Default');
  const [senderName, setSenderName] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [phone, setPhone] = useState('');
  const [signOff, setSignOff] = useState('Best regards');
  const [customSignOff, setCustomSignOff] = useState('');
  const [isDefaultNew, setIsDefaultNew] = useState(false);
  const [isDefaultReply, setIsDefaultReply] = useState(false);
  const [saving, setSaving] = useState(false);

  const signOffOptions = ['Best regards', 'Regards', 'Kind regards', 'Thanks', 'Cheers', 'Custom'];

  const loadSignatures = async () => {
    try {
      setLoading(true);
      const res = await api.signatures.list();
      if (res?.data) {
        setSignatures(res.data);
      }
    } catch {
      toast.error('Failed to load email signatures');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSignatures();
  }, []);

  const activeSignOff = signOff === 'Custom' ? (customSignOff || 'Best regards') : signOff;

  const buildPreviewText = () => {
    const lines = [activeSignOff, senderName || 'Your Name'];
    if (jobTitle && company) lines.push(`${jobTitle} | ${company}`);
    else if (jobTitle) lines.push(jobTitle);
    else if (company) lines.push(company);
    if (phone) lines.push(phone);
    return lines.join('\n');
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim() || !senderName.trim()) {
      toast.error('Signature name and sender name are required');
      return;
    }

    setSaving(true);
    try {
      const preview = buildPreviewText();
      await api.signatures.create({
        name: name.trim(),
        sender_name: senderName.trim(),
        job_title: jobTitle.trim() || null,
        company: company.trim() || null,
        phone: phone.trim() || null,
        sign_off: signOff,
        custom_sign_off: signOff === 'Custom' ? customSignOff.trim() : null,
        content_text: preview,
        is_default_new: isDefaultNew,
        is_default_reply: isDefaultReply,
      });

      toast.success('Signature saved successfully');
      setIsCreating(false);
      setName('New Signature');
      loadSignatures();
    } catch (err) {
      toast.error(err?.message || 'Failed to save signature');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.signatures.delete(id);
      toast.success('Signature deleted');
      setSignatures((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      toast.error(err?.message || 'Could not delete signature');
    }
  };

  const handleSetDefault = async (sig, type) => {
    try {
      const payload = type === 'new' ? { is_default_new: true } : { is_default_reply: true };
      await api.signatures.update(sig.id, payload);
      toast.success(`Updated default ${type === 'new' ? 'new email' : 'reply'} signature`);
      loadSignatures();
    } catch (err) {
      toast.error(err?.message || 'Failed to update default signature');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <PenTool className="w-4 h-4 text-blue-500" />
            Email Signatures & Personalization
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Create professional signatures with custom sign-offs, designations, and auto-insertion.
          </p>
        </div>
        {!isCreating && (
          <button
            type="button"
            onClick={() => setIsCreating(true)}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            New Signature
          </button>
        )}
      </div>

      {/* Signature List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {signatures.map((sig) => (
          <div
            key={sig.id}
            className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between space-y-3"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
                  {sig.name}
                </span>
                <button
                  type="button"
                  onClick={() => handleDelete(sig.id)}
                  aria-label="Delete signature"
                  className="p-1 text-slate-400 hover:text-red-500 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Badges */}
              <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                {sig.is_default_new && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
                    Default for New
                  </span>
                )}
                {sig.is_default_reply && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                    Default for Replies
                  </span>
                )}
              </div>

              {/* Text Preview */}
              <div className="mt-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-950 text-xs text-slate-700 dark:text-slate-300 font-mono whitespace-pre-wrap border border-slate-100 dark:border-slate-800/80">
                {sig.content_text}
              </div>
            </div>

            {/* Quick Default Actions */}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800/60 flex items-center justify-end gap-2 text-xs">
              {!sig.is_default_new && (
                <button
                  type="button"
                  onClick={() => handleSetDefault(sig, 'new')}
                  className="text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 font-medium"
                >
                  Set New Default
                </button>
              )}
              {!sig.is_default_reply && (
                <button
                  type="button"
                  onClick={() => handleSetDefault(sig, 'reply')}
                  className="text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium"
                >
                  Set Reply Default
                </button>
              )}
            </div>
          </div>
        ))}

        {signatures.length === 0 && !loading && !isCreating && (
          <div className="col-span-full py-8 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
            <PenTool className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">No signatures configured yet</p>
            <p className="text-xs text-slate-400 mt-0.5">Click New Signature to personalize your outbound emails.</p>
          </div>
        )}
      </div>

      {/* Signature Creation Modal / Form */}
      {isCreating && (
        <form
          onSubmit={handleCreate}
          className="p-5 rounded-2xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/20 dark:bg-blue-950/20 space-y-4 animate-fade-in"
        >
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-blue-500" />
              Create Signature
            </h4>
            <button
              type="button"
              onClick={() => setIsCreating(false)}
              className="text-xs text-slate-500 hover:underline"
            >
              Cancel
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Signature Identifier
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Work Signature"
                className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                placeholder="e.g. Roshan Kumar"
                className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Job Title / Designation
              </label>
              <input
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g. Lead Software Architect"
                className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Company
              </label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. MailMind AI"
                className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Sign-off Style
              </label>
              <select
                value={signOff}
                onChange={(e) => setSignOff(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
              >
                {signOffOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            {signOff === 'Custom' && (
              <div>
                <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                  Custom Sign-off Text
                </label>
                <input
                  type="text"
                  value={customSignOff}
                  onChange={(e) => setCustomSignOff(e.target.value)}
                  placeholder="e.g. Warmly,"
                  className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
                />
              </div>
            )}

            <div>
              <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                Phone (Optional)
              </label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 (555) 019-2831"
                className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
              />
            </div>
          </div>

          {/* Defaults Checkbox */}
          <div className="flex items-center gap-6 text-xs text-slate-700 dark:text-slate-300 pt-1">
            <label className="flex items-center gap-2 cursor-pointer font-medium">
              <input
                type="checkbox"
                checked={isDefaultNew}
                onChange={(e) => setIsDefaultNew(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              Use as default for New Emails
            </label>
            <label className="flex items-center gap-2 cursor-pointer font-medium">
              <input
                type="checkbox"
                checked={isDefaultReply}
                onChange={(e) => setIsDefaultReply(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              Use as default for AI Replies
            </label>
          </div>

          {/* Live Preview */}
          <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
            <span className="font-bold text-slate-500 uppercase tracking-wider text-[10px] flex items-center gap-1 mb-2">
              <Eye className="w-3.5 h-3.5 text-blue-500" />
              Live Signature Preview
            </span>
            <div className="font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
              {buildPreviewText()}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreating(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Signature'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
