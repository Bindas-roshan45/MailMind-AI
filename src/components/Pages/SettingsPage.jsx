import { useState } from 'react';
import {
  Settings, Mail, Bot, Bell, Moon, Sun, RefreshCw, Save, ArrowLeft,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const { user, theme, toggleTheme, setCurrentPage } = useApp();

  const [syncInterval, setSyncInterval] = useState('2');
  const [autoSync, setAutoSync] = useState(true);
  const [model, setModel] = useState('gemini-1.5-pro');
  const [defaultTone, setDefaultTone] = useState('professional');
  const [autoDraft, setAutoDraft] = useState(true);
  const [phishingShield, setPhishingShield] = useState(true);
  const [pushNotifs, setPushNotifs] = useState(true);
  const [soundAlerts, setSoundAlerts] = useState(false);
  const [dailyDigest, setDailyDigest] = useState(true);
  const [activeTab, setActiveTab] = useState('general');

  const handleSave = () => {
    toast.success('Settings saved successfully');
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto p-4 sm:p-6 bg-[#F5F7FC] dark:bg-[#0F172A] space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentPage('inbox')}
            className="p-2 rounded-lg bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white transition-colors"
            title="Back to inbox"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-[#1E293B] dark:text-white">Settings & Preferences</h1>
            <p className="text-xs text-[#7B8497] mt-0.5">
              Configure Gmail sync, AI models, security and notification preferences
            </p>
          </div>
        </div>

        <button
          onClick={handleSave}
          className="btn-primary text-xs py-2 px-4 flex items-center gap-1.5 shadow-sm"
        >
          <Save className="w-4 h-4" />
          <span>Save Changes</span>
        </button>
      </div>

      {/* Tabs Row */}
      <div className="flex items-center gap-2 border-b border-[#E5EAF2] dark:border-[#334155] pb-2 overflow-x-auto no-scrollbar">
        {[
          { id: 'general',       label: 'General & Appearance', icon: Settings },
          { id: 'ai',            label: 'AI & Reply Engine',     icon: Bot },
          { id: 'gmail',         label: 'Gmail & Sync',          icon: Mail },
          { id: 'notifications', label: 'Notifications',         icon: Bell },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors shrink-0 ${
                isActive
                  ? 'bg-[#4169E1] text-white shadow-xs'
                  : 'text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white hover:bg-white dark:hover:bg-[#1E293B]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Settings Sections */}
      <div className="space-y-6 max-w-4xl">
        {activeTab === 'general' && (
          <div className="space-y-4">
            <div className="card-white p-5 space-y-4">
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white">Appearance & Theme</h2>
              <div className="flex items-center justify-between py-2 border-b border-[#E5EAF2] dark:border-[#334155]">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Interface Theme</p>
                  <p className="text-[11px] text-[#7B8497]">Toggle between Light and Dark mode</p>
                </div>
                <div className="flex items-center gap-2 bg-[#F5F7FC] dark:bg-[#0F172A] p-1 rounded-lg border border-[#E5EAF2] dark:border-[#334155]">
                  <button
                    onClick={() => { if (theme !== 'light') toggleTheme(); }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                      theme === 'light'
                        ? 'bg-white text-[#4169E1] shadow-xs'
                        : 'text-[#7B8497] hover:text-[#1E293B]'
                    }`}
                  >
                    <Sun className="w-3.5 h-3.5" /> Light
                  </button>
                  <button
                    onClick={() => { if (theme !== 'dark') toggleTheme(); }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                      theme === 'dark'
                        ? 'bg-[#1E293B] text-[#93C5FD] shadow-xs'
                        : 'text-[#7B8497] hover:text-white'
                    }`}
                  >
                    <Moon className="w-3.5 h-3.5" /> Dark
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Layout Density</p>
                  <p className="text-[11px] text-[#7B8497]">Control whitespace and item padding</p>
                </div>
                <select className="input-minimal w-40 cursor-pointer text-xs">
                  <option value="comfortable">Comfortable</option>
                  <option value="compact">Compact</option>
                </select>
              </div>
            </div>

            <div className="card-white p-5 space-y-3">
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white">Account Profile</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[11px] text-[#7B8497] mb-1 font-medium">Display Name</label>
                  <input type="text" defaultValue={user.name} className="input-minimal" />
                </div>
                <div>
                  <label className="block text-[11px] text-[#7B8497] mb-1 font-medium">Primary Email</label>
                  <input type="email" defaultValue={user.email} disabled className="input-minimal opacity-70 cursor-not-allowed" />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-4">
            <div className="card-white p-5 space-y-4">
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white">AI Model & Generation Parameters</h2>

              <div className="flex items-center justify-between py-2 border-b border-[#E5EAF2] dark:border-[#334155]">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">AI Engine Provider</p>
                  <p className="text-[11px] text-[#7B8497]">Primary intelligence powering auto-replies and summaries</p>
                </div>
                <select
                  value={model}
                  onChange={e => setModel(e.target.value)}
                  className="input-minimal w-52 cursor-pointer text-xs font-medium"
                >
                  <option value="gemini-1.5-pro">Google Gemini 1.5 Pro</option>
                  <option value="gemini-1.5-flash">Google Gemini 1.5 Flash</option>
                  <option value="gpt-4o">OpenAI GPT-4o</option>
                  <option value="claude-3-5">Anthropic Claude 3.5 Sonnet</option>
                </select>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-[#E5EAF2] dark:border-[#334155]">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Default Reply Tone</p>
                  <p className="text-[11px] text-[#7B8497]">Tone applied to newly generated email drafts</p>
                </div>
                <select
                  value={defaultTone}
                  onChange={e => setDefaultTone(e.target.value)}
                  className="input-minimal w-40 cursor-pointer text-xs capitalize"
                >
                  <option value="professional">Professional</option>
                  <option value="friendly">Friendly</option>
                  <option value="short">Short</option>
                  <option value="detailed">Detailed</option>
                </select>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-[#E5EAF2] dark:border-[#334155]">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Auto-Draft Responses</p>
                  <p className="text-[11px] text-[#7B8497]">Pre-generate AI replies for inquiries marked high priority</p>
                </div>
                <input
                  type="checkbox"
                  checked={autoDraft}
                  onChange={e => setAutoDraft(e.target.checked)}
                  className="w-4 h-4 accent-[#4169E1] rounded cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Phishing & Suspicious Alert</p>
                  <p className="text-[11px] text-[#7B8497]">Analyze message content for deceptive links and scam patterns</p>
                </div>
                <input
                  type="checkbox"
                  checked={phishingShield}
                  onChange={e => setPhishingShield(e.target.checked)}
                  className="w-4 h-4 accent-[#4169E1] rounded cursor-pointer"
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'gmail' && (
          <div className="space-y-4">
            <div className="card-white p-5 space-y-4">
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white">Gmail Integration Status</h2>

              <div className="p-3.5 rounded-lg border border-emerald-200 dark:border-emerald-800/40 bg-emerald-50/50 dark:bg-emerald-950/20 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold text-xs">
                    G
                  </div>
                  <div>
                    <p className="text-xs font-bold text-[#1E293B] dark:text-white">{user.email}</p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[11px] font-medium text-emerald-700 dark:text-emerald-400">OAuth 2.0 Connected</span>
                      <span className="text-[11px] text-[#7B8497]">• Last synced 2 min ago</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => toast.success('Syncing Gmail inbox now...')}
                  className="btn-secondary text-xs flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-[#4169E1]" />
                  <span>Sync Now</span>
                </button>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-[#E5EAF2] dark:border-[#334155]">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Background Auto-Sync</p>
                  <p className="text-[11px] text-[#7B8497]">Poll Gmail API periodically for new messages</p>
                </div>
                <input
                  type="checkbox"
                  checked={autoSync}
                  onChange={e => setAutoSync(e.target.checked)}
                  className="w-4 h-4 accent-[#4169E1] rounded cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Sync Frequency</p>
                  <p className="text-[11px] text-[#7B8497]">How often MailMind queries for inbox updates</p>
                </div>
                <select
                  value={syncInterval}
                  onChange={e => setSyncInterval(e.target.value)}
                  className="input-minimal w-40 cursor-pointer text-xs"
                >
                  <option value="1">Every 1 minute</option>
                  <option value="2">Every 2 minutes</option>
                  <option value="5">Every 5 minutes</option>
                  <option value="15">Every 15 minutes</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="space-y-4">
            <div className="card-white p-5 space-y-4">
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white">Push & In-App Notifications</h2>

              <div className="flex items-center justify-between py-2 border-b border-[#E5EAF2] dark:border-[#334155]">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Web Push Notifications</p>
                  <p className="text-[11px] text-[#7B8497]">Show browser alerts when an AI reply draft is ready</p>
                </div>
                <input
                  type="checkbox"
                  checked={pushNotifs}
                  onChange={e => setPushNotifs(e.target.checked)}
                  className="w-4 h-4 accent-[#4169E1] rounded cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between py-2 border-b border-[#E5EAF2] dark:border-[#334155]">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Audio Chime on Urgent Inquiries</p>
                  <p className="text-[11px] text-[#7B8497]">Play a subtle sound when a high-urgency message arrives</p>
                </div>
                <input
                  type="checkbox"
                  checked={soundAlerts}
                  onChange={e => setSoundAlerts(e.target.checked)}
                  className="w-4 h-4 accent-[#4169E1] rounded cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-xs font-semibold text-[#1E293B] dark:text-white">Daily Executive Digest</p>
                  <p className="text-[11px] text-[#7B8497]">Receive a morning summary of remaining follow-ups and tasks</p>
                </div>
                <input
                  type="checkbox"
                  checked={dailyDigest}
                  onChange={e => setDailyDigest(e.target.checked)}
                  className="w-4 h-4 accent-[#4169E1] rounded cursor-pointer"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
