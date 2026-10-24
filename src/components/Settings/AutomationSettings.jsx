import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  PauseCircle,
  PlayCircle,
  Plus,
  Trash2,
  History,
  Sliders,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../services/api';

export default function AutomationSettings() {
  const [rules, setRules] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const [automationMode, setAutomationMode] = useState('draft_only');
  const [dailyLimit, setDailyLimit] = useState(20);
  const [confidenceScore, setConfidenceScore] = useState(85);
  const [isCreatingRule, setIsCreatingRule] = useState(false);

  // New Rule Form State
  const [ruleName, setRuleName] = useState('');
  const [ruleCategory, setRuleCategory] = useState('Client');
  const [ruleKeywords, setRuleKeywords] = useState('');
  const [ruleSenderPattern, setRuleSenderPattern] = useState('');
  const [ruleTemplate, setRuleTemplate] = useState('');
  const [ruleAutoSend, setRuleAutoSend] = useState(false);
  const [savingRule, setSavingRule] = useState(false);

  const categories = ['Work', 'Client', 'Finance', 'Personal', 'Meeting', 'Promotion'];

  const loadData = async () => {
    try {
      setLoading(true);
      const [rulesRes, logsRes, prefRes] = await Promise.all([
        api.automation.listRules(),
        api.automation.getLogs(15),
        api.preferences.get(),
      ]);

      if (rulesRes?.data) setRules(rulesRes.data);
      if (logsRes?.data) setLogs(logsRes.data);
      if (prefRes?.data) {
        setPaused(Boolean(prefRes.data.automation_paused));
        setAutomationMode(prefRes.data.automation_mode || 'draft_only');
        setDailyLimit(prefRes.data.daily_reply_limit ?? 20);
        setConfidenceScore(prefRes.data.min_confidence_score ?? 85);
      }
    } catch {
      toast.error('Failed to load automation settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTogglePause = async () => {
    const nextState = !paused;
    setPaused(nextState);
    try {
      await api.automation.togglePause(nextState);
      toast.success(nextState ? 'Automation paused globally' : 'Automation resumed');
    } catch {
      setPaused(!nextState);
      toast.error('Failed to update pause switch');
    }
  };

  const handleSavePreferences = async () => {
    try {
      await api.preferences.update({
        automation_mode: automationMode,
        daily_reply_limit: Number(dailyLimit),
        min_confidence_score: Number(confidenceScore),
      });
      toast.success('Automation preferences saved');
    } catch (err) {
      toast.error(err?.message || 'Failed to save automation preferences');
    }
  };

  const handleToggleRule = async (id) => {
    try {
      const res = await api.automation.toggleRule(id);
      if (res?.data) {
        setRules((prev) =>
          prev.map((r) => (r.id === id ? { ...r, is_active: res.data.is_active } : r))
        );
        toast.success(res.message || 'Rule status updated');
      }
    } catch {
      toast.error('Failed to toggle rule');
    }
  };

  const handleDeleteRule = async (id) => {
    try {
      await api.automation.deleteRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
      toast.success('Rule deleted');
    } catch {
      toast.error('Failed to delete rule');
    }
  };

  const handleCreateRule = async (e) => {
    e.preventDefault();
    if (!ruleName.trim() || !ruleTemplate.trim()) {
      toast.error('Rule name and reply template are required');
      return;
    }

    setSavingRule(true);
    try {
      const kw = ruleKeywords
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean);

      const res = await api.automation.createRule({
        name: ruleName.trim(),
        category: ruleCategory,
        sender_pattern: ruleSenderPattern.trim() || null,
        keywords: kw,
        reply_template: ruleTemplate.trim(),
        auto_send: ruleAutoSend,
        is_active: true,
      });

      if (res?.data) {
        toast.success('Rule created successfully');
        setIsCreatingRule(false);
        setRuleName('');
        setRuleKeywords('');
        setRuleSenderPattern('');
        setRuleTemplate('');
        setRuleAutoSend(false);
        loadData();
      }
    } catch (err) {
      toast.error(err?.message || 'Could not create rule');
    } finally {
      setSavingRule(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Emergency Global Pause Switch */}
      <div
        className={`p-5 rounded-2xl border transition-all ${
          paused
            ? 'bg-amber-500/10 border-amber-300 dark:border-amber-600/40 text-amber-900 dark:text-amber-100'
            : 'bg-emerald-500/10 border-emerald-300 dark:border-emerald-600/40 text-emerald-900 dark:text-emerald-100'
        } flex items-center justify-between gap-4 flex-wrap`}
      >
        <div className="flex items-center gap-3">
          {paused ? (
            <PauseCircle className="w-8 h-8 text-amber-600 dark:text-amber-400 shrink-0" />
          ) : (
            <PlayCircle className="w-8 h-8 text-emerald-600 dark:text-emerald-400 shrink-0" />
          )}
          <div>
            <h4 className="text-sm font-bold">
              Global Automation Status: {paused ? 'PAUSED' : 'ACTIVE & RUNNING'}
            </h4>
            <p className="text-xs opacity-90 mt-0.5">
              {paused
                ? 'All automatic actions are halted. Inbound messages create drafts for human review only.'
                : 'Safety rules and auto-reply filters are active and evaluating incoming emails.'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleTogglePause}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm ${
            paused
              ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
              : 'bg-amber-600 hover:bg-amber-700 text-white'
          }`}
        >
          {paused ? 'Resume Automation' : 'Emergency Pause All'}
        </button>
      </div>

      {/* Safety Guardrails & Mode Parameters */}
      <div className="card-white p-5 space-y-4">
        <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Sliders className="w-4 h-4 text-blue-500" />
          Automation Mode & Safety Limits
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Default Action Mode
            </label>
            <select
              value={automationMode}
              onChange={(e) => setAutomationMode(e.target.value)}
              className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
            >
              <option value="draft_only">Draft Only (Recommended — Never Auto-Send)</option>
              <option value="approval_required">Approval Required (Prompt Review Modal)</option>
              <option value="auto_reply">Auto-Reply (Send only on Explicit Safe Rules)</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Daily Auto-Reply Limit
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(e.target.value)}
              className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Minimum Confidence Score ({confidenceScore}%)
            </label>
            <input
              type="range"
              min="60"
              max="98"
              value={confidenceScore}
              onChange={(e) => setConfidenceScore(e.target.value)}
              className="w-full accent-blue-600 mt-2 cursor-pointer"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={handleSavePreferences}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
          >
            Save Automation Settings
          </button>
        </div>
      </div>

      {/* Rules Manager */}
      <div className="card-white p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-indigo-500" />
              Configured Automation Rules
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Rules execute only if sensitive topics and phishing checks pass.
            </p>
          </div>
          {!isCreatingRule && (
            <button
              type="button"
              onClick={() => setIsCreatingRule(true)}
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Rule
            </button>
          )}
        </div>

        {/* Rule List */}
        <div className="space-y-3">
          {rules.map((r) => (
            <div
              key={r.id}
              className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex items-center justify-between gap-3 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-slate-800 dark:text-slate-100">{r.name}</span>
                  {r.category && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
                      {r.category}
                    </span>
                  )}
                  {r.auto_send ? (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300">
                      Auto-Send Enabled
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      Draft Only
                    </span>
                  )}
                </div>
                <p className="text-slate-600 dark:text-slate-400 line-clamp-1 italic">
                  &quot;{r.reply_template}&quot;
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleToggleRule(r.id)}
                  className={`px-3 py-1 rounded-lg font-semibold text-[11px] transition-colors ${
                    r.is_active
                      ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300'
                      : 'bg-slate-200 dark:bg-slate-800 text-slate-500'
                  }`}
                >
                  {r.is_active ? 'Active' : 'Disabled'}
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteRule(r.id)}
                  className="p-1 text-slate-400 hover:text-red-500 rounded transition-colors"
                  aria-label="Delete rule"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}

          {rules.length === 0 && !loading && !isCreatingRule && (
            <p className="text-xs text-slate-400 italic text-center py-4">
              No custom rules created yet.
            </p>
          )}
        </div>

        {/* New Rule Modal / Inline Form */}
        {isCreatingRule && (
          <form
            onSubmit={handleCreateRule}
            className="p-4 rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/20 dark:bg-blue-950/20 space-y-3 text-xs animate-fade-in"
          >
            <div className="flex items-center justify-between font-bold text-slate-900 dark:text-white">
              <span>Create Safe Automation Rule</span>
              <button
                type="button"
                onClick={() => setIsCreatingRule(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold mb-1 text-slate-600 dark:text-slate-300">
                  Rule Name
                </label>
                <input
                  type="text"
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  placeholder="e.g. Schedule Request Auto-Confirm"
                  className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold mb-1 text-slate-600 dark:text-slate-300">
                  Category Match
                </label>
                <select
                  value={ruleCategory}
                  onChange={(e) => setRuleCategory(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                >
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-1 text-slate-600 dark:text-slate-300">
                  Keywords (comma separated)
                </label>
                <input
                  type="text"
                  value={ruleKeywords}
                  onChange={(e) => setRuleKeywords(e.target.value)}
                  placeholder="e.g. demo, pricing, consultation"
                  className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1 text-slate-600 dark:text-slate-300">
                  Sender Pattern (Wildcard)
                </label>
                <input
                  type="text"
                  value={ruleSenderPattern}
                  onChange={(e) => setRuleSenderPattern(e.target.value)}
                  placeholder="e.g. *@partnercorp.com"
                  className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold mb-1 text-slate-600 dark:text-slate-300">
                Reply Template
              </label>
              <textarea
                rows={3}
                value={ruleTemplate}
                onChange={(e) => setRuleTemplate(e.target.value)}
                placeholder="Hi, thank you for reaching out. We have logged your request..."
                className="w-full p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                required
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer font-semibold text-amber-700 dark:text-amber-400">
              <input
                type="checkbox"
                checked={ruleAutoSend}
                onChange={(e) => setRuleAutoSend(e.target.checked)}
                className="rounded border-slate-300 text-amber-600 focus:ring-amber-500"
              />
              Authorize Auto-Sending (Only sends if email is confirmed safe & passes sensitivity filter)
            </label>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsCreatingRule(false)}
                className="px-3 py-1.5 rounded-lg text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingRule}
                className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-sm"
              >
                {savingRule ? 'Saving...' : 'Save Rule'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Activity & Audit Logs */}
      <div className="card-white p-5 space-y-3">
        <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <History className="w-4 h-4 text-slate-500" />
          Recent Automation Audit History
        </h4>
        <div className="space-y-2 text-xs">
          {logs.map((log) => (
            <div
              key={log.id}
              className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 flex items-center justify-between gap-3"
            >
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      log.action_taken === 'AUTO_REPLIED'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                        : log.action_taken === 'DRAFT_CREATED'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                        : log.action_taken === 'BLOCKED_SENSITIVE'
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                        : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                    }`}
                  >
                    {log.action_taken}
                  </span>
                  <span className="text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                    Msg: {log.message_id}
                  </span>
                </div>
                <p className="text-slate-500 dark:text-slate-400 text-[11px]">{log.reason}</p>
              </div>
              <span className="text-[10px] text-slate-400 shrink-0">
                {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ''}
              </span>
            </div>
          ))}

          {logs.length === 0 && (
            <p className="text-xs text-slate-400 italic text-center py-2">
              No automation actions logged yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
