import { useState, useMemo } from 'react';
import {
  BarChart3, TrendingUp, Clock, CheckCircle2, AlertTriangle, Mail,
  ArrowLeft, Calendar, Zap, CheckSquare, Bot, Sparkles,
  FileSpreadsheet, FileText, Check, Eye, PieChart as PieIcon,
  ExternalLink,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { useApp } from '../../context/AppContext';
import toast from 'react-hot-toast';

// ─── Chart Custom Tooltip ─────────────────────────────────────────
const CustomBarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-lg p-3 text-xs">
      <p className="font-bold text-[#1E293B] dark:text-white mb-1.5">{label}</p>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-4 text-[#4169E1]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#4169E1]" />
            Received:
          </span>
          <span className="font-semibold">{payload[0]?.value}</span>
        </div>
        <div className="flex items-center justify-between gap-4 text-[#8B5CF6]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#8B5CF6]" />
            Replied:
          </span>
          <span className="font-semibold">{payload[1]?.value}</span>
        </div>
      </div>
    </div>
  );
};

const CustomPieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const data = payload[0];
  return (
    <div className="bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-lg px-3 py-2 text-xs">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: data.payload.color }} />
        <span className="font-bold text-[#1E293B] dark:text-white">{data.name}:</span>
        <span className="text-[#4169E1] font-semibold">{data.value}%</span>
        <span className="text-[#7B8497]">({data.payload.count} emails)</span>
      </div>
    </div>
  );
};

export default function ReportsPage() {
  const { setCurrentPage, tasks, toggleTask } = useApp();

  // Date Range filter: 'today' | '7d' | '30d' | 'custom'
  const [dateRange, setDateRange] = useState('7d');
  const [customStart, setCustomStart] = useState('2026-10-01');
  const [customEnd, setCustomEnd] = useState('2026-10-13');

  // AI Reply Modes Toggles
  const [autoReplyEnabled, setAutoReplyEnabled] = useState(true);
  const [aiDraftEnabled, setAiDraftEnabled] = useState(true);
  const [smartThreshold, setSmartThreshold] = useState(true);

  // Notification toggles
  const [notifChannels, setNotifChannels] = useState({
    email: true,
    browser: true,
    mobile: true,
  });

  // Calendar meeting states
  const [addedMeetings, setAddedMeetings] = useState(new Set());

  // ─── Filtered Data By Range ──────────────────────────────────────
  const rangeData = useMemo(() => {
    switch (dateRange) {
      case 'today':
        return {
          label: 'Today',
          received: 24,
          replied: 10,
          pending: 4,
          urgent: 2,
          read: 19,
          unread: 5,
          autoReplies: 6,
          aiDrafts: 8,
          awaitingApproval: 2,
          userEdited: 1,
          timeSaved: '1.8 hrs',
          replyRate: '83.3%',
          avgResponse: '11.5 mins',
          activity: [
            { label: '9 AM', received: 4, replied: 2 },
            { label: '11 AM', received: 7, replied: 3 },
            { label: '1 PM', received: 3, replied: 2 },
            { label: '3 PM', received: 5, replied: 2 },
            { label: '5 PM', received: 3, replied: 1 },
            { label: '7 PM', received: 2, replied: 0 },
          ],
        };
      case '30d':
        return {
          label: 'Last 30 Days',
          received: 548,
          replied: 164,
          pending: 28,
          urgent: 14,
          read: 480,
          unread: 68,
          autoReplies: 118,
          aiDrafts: 182,
          awaitingApproval: 16,
          userEdited: 22,
          timeSaved: '29.4 hrs',
          replyRate: '81.2%',
          avgResponse: '15.8 mins',
          activity: [
            { label: 'Week 1', received: 130, replied: 42 },
            { label: 'Week 2', received: 145, replied: 48 },
            { label: 'Week 3', received: 138, replied: 39 },
            { label: 'Week 4', received: 135, replied: 35 },
          ],
        };
      case 'custom':
        return {
          label: `${customStart} - ${customEnd}`,
          received: 186,
          replied: 58,
          pending: 18,
          urgent: 7,
          read: 154,
          unread: 32,
          autoReplies: 42,
          aiDrafts: 64,
          awaitingApproval: 8,
          userEdited: 7,
          timeSaved: '10.2 hrs',
          replyRate: '79.5%',
          avgResponse: '13.8 mins',
          activity: [
            { label: 'Oct 01-03', received: 42, replied: 14 },
            { label: 'Oct 04-06', received: 48, replied: 15 },
            { label: 'Oct 07-09', received: 50, replied: 16 },
            { label: 'Oct 10-13', received: 46, replied: 13 },
          ],
        };
      case '7d':
      default:
        return {
          label: 'Last 7 Days',
          received: 124,
          replied: 36,
          pending: 12,
          urgent: 5,
          read: 102,
          unread: 22,
          autoReplies: 28,
          aiDrafts: 42,
          awaitingApproval: 6,
          userEdited: 5,
          timeSaved: '6.8 hrs',
          replyRate: '78.4%',
          avgResponse: '14.2 mins',
          activity: [
            { label: 'Mon', received: 18, replied: 6 },
            { label: 'Tue', received: 24, replied: 10 },
            { label: 'Wed', received: 14, replied: 8 },
            { label: 'Thu', received: 32, replied: 12 },
            { label: 'Fri', received: 20, replied: 9 },
            { label: 'Sat', received: 8, replied: 4 },
            { label: 'Sun', received: 8, replied: 5 },
          ],
        };
    }
  }, [dateRange, customStart, customEnd]);

  // Categories distribution
  const CATEGORIES = [
    { name: 'Work', value: 35, count: Math.round(rangeData.received * 0.35), color: '#4169E1' },
    { name: 'College', value: 20, count: Math.round(rangeData.received * 0.20), color: '#22C55E' },
    { name: 'Client', value: 18, count: Math.round(rangeData.received * 0.18), color: '#F97316' },
    { name: 'Personal', value: 12, count: Math.round(rangeData.received * 0.12), color: '#EC4899' },
    { name: 'Promotions', value: 15, count: Math.round(rangeData.received * 0.15), color: '#A855F7' },
  ];

  // Tasks statistics
  const completedTasks = tasks.filter(t => t.done).length;
  const pendingTasks = tasks.filter(t => !t.done).length;
  const overdueTasks = 1; // 1 overdue simulated
  const highPriorityTasks = tasks.filter(t => t.priority === 'high').length;
  const mediumPriorityTasks = tasks.filter(t => t.priority === 'medium').length;
  const lowPriorityTasks = tasks.filter(t => t.priority === 'low').length;

  // Calendar Meetings
  const MEETINGS = [
    {
      id: 'm-1',
      title: 'Team Meeting',
      time: 'Tomorrow, 11:00 AM - 12:00 PM',
      platform: 'Google Meet',
      detectedFrom: 'Meeting Confirmation (Sarah Team)',
      category: 'Work',
    },
    {
      id: 'm-2',
      title: 'Website Project Inquiry Sync',
      time: 'Wed, Oct 14, 10:00 AM - 10:30 AM',
      platform: 'Google Meet',
      detectedFrom: 'Website Project Inquiry (John Smith)',
      category: 'Client',
    },
    {
      id: 'm-3',
      title: 'Q3 Strategy & Performance Review',
      time: 'Fri, Oct 16, 2:00 PM - 3:00 PM',
      platform: 'Conference Room B',
      detectedFrom: 'Q3 Product Strategy Review',
      category: 'Work',
    },
  ];

  // Export CSV
  const handleExportCSV = () => {
    try {
      const csvRows = [
        ['"MailMind AI — Reports Dashboard Summary"'],
        [`"Date Range: ${rangeData.label}"`, `"Generated At: ${new Date().toLocaleString()}"`],
        ['"Data Status: Demo Data (Simulated Preview)"'],
        [''],
        ['"=== 1. EMAIL STATISTICS ==="'],
        ['"Metric"', '"Value"'],
        ['"Total Received"', rangeData.received],
        ['"Emails Replied"', rangeData.replied],
        ['"Pending Replies"', rangeData.pending],
        ['"Urgent Emails"', rangeData.urgent],
        ['"Read Emails"', rangeData.read],
        ['"Unread Emails"', rangeData.unread],
        ['"Reply Rate"', rangeData.replyRate],
        ['"Average Response Time"', rangeData.avgResponse],
        [''],
        ['"=== 2. AI REPLY MODES & AUTOMATION ==="'],
        ['"Metric"', '"Value"'],
        ['"Auto Replies Sent"', rangeData.autoReplies],
        ['"AI Drafts Generated"', rangeData.aiDrafts],
        ['"Replies Awaiting Approval"', rangeData.awaitingApproval],
        ['"Replies Edited by User"', rangeData.userEdited],
        ['"AI Success Rate"', '"96.4%"'],
        ['"Review / Flagged Rate"', '"3.6%"'],
        ['"Time Saved by AI"', rangeData.timeSaved],
        [''],
        ['"=== 3. CATEGORY DISTRIBUTION ==="'],
        ['"Category"', '"Percentage"', '"Email Count"'],
        ...CATEGORIES.map(c => [`"${c.name}"`, `"${c.value}%"`, c.count]),
        [''],
        ['"=== 4. TASKS & DEADLINES ==="'],
        ['"Task Title"', '"Due Date"', '"Priority"', '"Status"'],
        ...tasks.map(t => [
          `"${t.title.replace(/"/g, '""')}"`,
          `"${t.dueDate}"`,
          `"${t.priority}"`,
          `"${t.done ? 'Completed' : 'Pending'}"`,
        ]),
        [''],
        ['"=== 5. CALENDAR MEETINGS ==="'],
        ['"Meeting Title"', '"Time"', '"Platform"', '"Source Email"'],
        ...MEETINGS.map(m => [
          `"${m.title}"`,
          `"${m.time}"`,
          `"${m.platform}"`,
          `"${m.detectedFrom}"`,
        ]),
      ];

      const csvContent = 'data:text/csv;charset=utf-8,' + csvRows.map(r => r.join(',')).join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `MailMind_Report_${dateRange}_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success(`Exported CSV for ${rangeData.label}`);
    } catch {
      toast.error('Failed to export CSV report');
    }
  };

  // Export PDF (Prints clean styled page)
  const handleExportPDF = () => {
    toast.success('Preparing print / PDF document...');
    setTimeout(() => {
      window.print();
    }, 400);
  };

  const handleAddCalendar = (id, title) => {
    setAddedMeetings(prev => new Set([...prev, id]));
    toast.success(`"${title}" added to your Calendar`);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto p-4 sm:p-6 bg-[#F5F7FC] dark:bg-[#0F172A] space-y-6">
      {/* ── Page Header ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-1 border-b border-[#E5EAF2] dark:border-[#334155]/60">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentPage('inbox')}
            className="p-2 rounded-lg bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white transition-colors shadow-xs"
            title="Back to Inbox"
            aria-label="Back to Inbox"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold text-[#1E293B] dark:text-white tracking-tight">
                Reports Dashboard
              </h1>
              {/* Demo Data Pill */}
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/40">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                Demo Data
              </span>
            </div>
            <p className="text-xs text-[#7B8497] dark:text-[#94A3B8] mt-1">
              Consolidated intelligence on email throughput, AI reply automation, upcoming tasks, and scheduling.
            </p>
          </div>
        </div>

        {/* Date Filter & Export Actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Date Filter Pills */}
          <div className="inline-flex p-1 rounded-xl bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] shadow-xs">
            {[
              { id: 'today', label: 'Today' },
              { id: '7d', label: 'Last 7 Days' },
              { id: '30d', label: 'Last 30 Days' },
              { id: 'custom', label: 'Custom' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setDateRange(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  dateRange === tab.id
                    ? 'bg-[#4169E1] text-white shadow-xs'
                    : 'text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Export CSV & PDF Buttons */}
          <button
            onClick={handleExportCSV}
            className="btn-secondary text-xs flex items-center gap-1.5 px-3 py-2 shadow-xs"
            title="Export CSV data"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-[#4169E1]" />
            <span className="hidden sm:inline font-medium">CSV</span>
          </button>

          <button
            onClick={handleExportPDF}
            className="btn-secondary text-xs flex items-center gap-1.5 px-3 py-2 shadow-xs"
            title="Export or Print PDF report"
          >
            <FileText className="w-3.5 h-3.5 text-red-500" />
            <span className="hidden sm:inline font-medium">PDF</span>
          </button>
        </div>
      </div>

      {/* Custom Date Range Picker (shown when custom is selected) */}
      {dateRange === 'custom' && (
        <div className="card-white p-3.5 flex items-center gap-3 flex-wrap animate-fade-in text-xs">
          <span className="font-semibold text-[#1E293B] dark:text-white flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-[#4169E1]" />
            Custom Date Range:
          </span>
          <div className="flex items-center gap-2">
            <label className="text-[#7B8497]">From:</label>
            <input
              type="date"
              value={customStart}
              onChange={e => setCustomStart(e.target.value)}
              className="px-2.5 py-1 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-white dark:bg-[#1E293B] text-[#1E293B] dark:text-white text-xs"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[#7B8497]">To:</label>
            <input
              type="date"
              value={customEnd}
              onChange={e => setCustomEnd(e.target.value)}
              className="px-2.5 py-1 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-white dark:bg-[#1E293B] text-[#1E293B] dark:text-white text-xs"
            />
          </div>
          <span className="text-[#7B8497] italic ml-auto">
            Viewing metrics for custom interval ({customStart} to {customEnd})
          </span>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          SECTION A: Email Statistics (Summary KPI Cards)
      ───────────────────────────────────────────────────────────────── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-[#1E293B] dark:text-white flex items-center gap-2">
            <Mail className="w-4 h-4 text-[#4169E1]" />
            <span>Email Statistics ({rangeData.label})</span>
          </h2>
          <span className="text-xs text-[#7B8497]">Live mock metrics updated every 2 mins</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {/* Total Emails Received */}
          <div className="card-white p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#7B8497]">Total Received</span>
              <div className="w-8 h-8 rounded-lg bg-[#E8EEFF] dark:bg-[#4169E1]/20 text-[#4169E1] dark:text-[#93C5FD] flex items-center justify-center">
                <Mail className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#1E293B] dark:text-white mt-2">
              {rangeData.received}
            </p>
            <div className="flex items-center gap-1.5 mt-1.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
              <TrendingUp className="w-3 h-3" />
              <span>+14.2% vs previous period</span>
            </div>
          </div>

          {/* Emails Replied To */}
          <div className="card-white p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#7B8497]">Emails Replied</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                <CheckCircle2 className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#1E293B] dark:text-white mt-2">
              {rangeData.replied}
            </p>
            <div className="flex items-center gap-1.5 mt-1.5 text-[11px] font-medium text-[#4169E1]">
              <Zap className="w-3 h-3" />
              <span>{rangeData.replyRate} response rate</span>
            </div>
          </div>

          {/* Pending Replies */}
          <div className="card-white p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#7B8497]">Pending Replies</span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 flex items-center justify-center">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-2">
              {rangeData.pending}
            </p>
            <p className="text-[11px] text-[#7B8497] mt-1.5">
              Avg wait: 2.4 hrs
            </p>
          </div>

          {/* Urgent Emails */}
          <div className="card-white p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#7B8497]">Urgent Emails</span>
              <div className="w-8 h-8 rounded-lg bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-2">
              {rangeData.urgent}
            </p>
            <span className="inline-block mt-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-950/60 text-red-700 dark:text-red-300">
              Needs Immediate Attention
            </span>
          </div>

          {/* Read / Unread Breakdown */}
          <div className="card-white p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#7B8497]">Read / Unread</span>
              <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                <Eye className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-2xl font-bold text-[#1E293B] dark:text-white">{rangeData.read}</span>
              <span className="text-xs text-[#7B8497]">read</span>
              <span className="text-base font-bold text-[#4169E1]">/ {rangeData.unread}</span>
              <span className="text-xs text-[#7B8497]">new</span>
            </div>
            {/* Read progress bar */}
            <div className="w-full bg-[#E5EAF2] dark:bg-[#334155] rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className="bg-[#4169E1] h-1.5 rounded-full"
                style={{ width: `${Math.round((rangeData.read / rangeData.received) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          SECTION B: AI Reply Modes (Combined Detailed Version)
      ───────────────────────────────────────────────────────────────── */}
      <section className="card-white p-5 space-y-4">
        <div className="flex items-start sm:items-center justify-between flex-wrap gap-2 pb-3 border-b border-[#E5EAF2] dark:border-[#334155]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#4169E1] to-[#8B5CF6] text-white flex items-center justify-center shadow-xs">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white flex items-center gap-2">
                <span>AI Reply Modes & Automation Performance</span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300">
                  Active
                </span>
              </h2>
              <p className="text-xs text-[#7B8497]">
                Configure autonomous replies and monitor draft approval metrics
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {rangeData.timeSaved} Saved by AI
            </span>
          </div>
        </div>

        {/* Reply Mode Interactive Toggles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          {/* Toggle 1: Auto Reply */}
          <div className="p-3.5 rounded-xl border border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#162032] flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[#1E293B] dark:text-white">Auto Reply</span>
                <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300">
                  {autoReplyEnabled ? 'ON' : 'OFF'}
                </span>
              </div>
              <p className="text-[11px] text-[#7B8497] leading-relaxed">
                Automatically replies to routine emails (confirmations, receipts, simple inquiries).
              </p>
            </div>
            <button
              onClick={() => {
                setAutoReplyEnabled(!autoReplyEnabled);
                toast.success(`Auto Reply ${!autoReplyEnabled ? 'enabled' : 'paused'}`);
              }}
              className={`w-10 h-6 shrink-0 rounded-full p-0.5 transition-colors duration-200 ease-in-out cursor-pointer ${
                autoReplyEnabled ? 'bg-[#4169E1]' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                  autoReplyEnabled ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Toggle 2: AI Draft + Confirmation */}
          <div className="p-3.5 rounded-xl border border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#162032] flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[#1E293B] dark:text-white">AI Draft + Confirmation</span>
                <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300">
                  {aiDraftEnabled ? 'ON' : 'OFF'}
                </span>
              </div>
              <p className="text-[11px] text-[#7B8497] leading-relaxed">
                AI generates full context replies; sends push notification for your 1-click review.
              </p>
            </div>
            <button
              onClick={() => {
                setAiDraftEnabled(!aiDraftEnabled);
                toast.success(`AI Draft + Review ${!aiDraftEnabled ? 'enabled' : 'paused'}`);
              }}
              className={`w-10 h-6 shrink-0 rounded-full p-0.5 transition-colors duration-200 ease-in-out cursor-pointer ${
                aiDraftEnabled ? 'bg-[#4169E1]' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                  aiDraftEnabled ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Toggle 3: Confidence Threshold */}
          <div className="p-3.5 rounded-xl border border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#162032] flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[#1E293B] dark:text-white">High Confidence Filter</span>
                <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300">
                  {smartThreshold ? '≥85%' : 'ALL'}
                </span>
              </div>
              <p className="text-[11px] text-[#7B8497] leading-relaxed">
                Only drafts replies when AI classification confidence exceeds 85% safety score.
              </p>
            </div>
            <button
              onClick={() => {
                setSmartThreshold(!smartThreshold);
                toast.success(`Confidence threshold ${!smartThreshold ? 'enforced' : 'relaxed'}`);
              }}
              className={`w-10 h-6 shrink-0 rounded-full p-0.5 transition-colors duration-200 ease-in-out cursor-pointer ${
                smartThreshold ? 'bg-[#4169E1]' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                  smartThreshold ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {/* AI Reply Statistics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
          <div className="p-3 rounded-xl bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-center">
            <p className="text-[11px] font-medium text-[#7B8497]">Auto Replies Sent</p>
            <p className="text-xl font-bold text-[#4169E1] mt-1">{rangeData.autoReplies}</p>
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400">100% delivered</span>
          </div>

          <div className="p-3 rounded-xl bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-center">
            <p className="text-[11px] font-medium text-[#7B8497]">AI Drafts Created</p>
            <p className="text-xl font-bold text-[#8B5CF6] mt-1">{rangeData.aiDrafts}</p>
            <span className="text-[10px] text-[#7B8497]">Full context</span>
          </div>

          <div className="p-3 rounded-xl bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-center">
            <p className="text-[11px] font-medium text-[#7B8497]">Awaiting Approval</p>
            <p className="text-xl font-bold text-amber-500 mt-1">{rangeData.awaitingApproval}</p>
            <span className="text-[10px] text-amber-600 dark:text-amber-400">Ready in inbox</span>
          </div>

          <div className="p-3 rounded-xl bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-center">
            <p className="text-[11px] font-medium text-[#7B8497]">Edited by User</p>
            <p className="text-xl font-bold text-[#1E293B] dark:text-white mt-1">{rangeData.userEdited}</p>
            <span className="text-[10px] text-[#7B8497]">Minor tweaks</span>
          </div>

          <div className="p-3 rounded-xl bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-center">
            <p className="text-[11px] font-medium text-[#7B8497]">Success Rate</p>
            <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">96.4%</p>
            <span className="text-[10px] text-emerald-600">High accuracy</span>
          </div>

          <div className="p-3 rounded-xl bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-center">
            <p className="text-[11px] font-medium text-[#7B8497]">Review / Flagged</p>
            <p className="text-xl font-bold text-slate-500 mt-1">3.6%</p>
            <span className="text-[10px] text-slate-500">Self-monitored</span>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          SECTION C: Email Analytics & Traffic (Charts & Distribution)
      ───────────────────────────────────────────────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Email Traffic & Daily Activity Bar Chart (2 cols) */}
        <div className="card-white p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#4169E1]" />
                <span>Email Activity & Replies ({rangeData.label})</span>
              </h2>
              <p className="text-xs text-[#7B8497]">
                Compare incoming email volume against outgoing user & AI replies
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-[#1E293B] dark:text-[#E2E8F0]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#4169E1]" /> Inbound Received
              </span>
              <span className="flex items-center gap-1.5 text-[#1E293B] dark:text-[#E2E8F0]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#8B5CF6]" /> Replied
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rangeData.activity} barSize={16} barGap={6}>
                <XAxis
                  dataKey="label"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#7B8497', fontSize: 11 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#7B8497', fontSize: 11 }}
                  width={30}
                />
                <Tooltip content={<CustomBarTooltip />} cursor={{ fill: 'rgba(65, 105, 225, 0.05)' }} />
                <Bar dataKey="received" fill="#4169E1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="replied" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Reply rate & Average response time stats bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-[#E5EAF2] dark:border-[#334155] text-xs">
            <div>
              <span className="text-[#7B8497]">Overall Reply Rate:</span>
              <p className="text-sm font-bold text-[#4169E1] mt-0.5">{rangeData.replyRate}</p>
            </div>
            <div>
              <span className="text-[#7B8497]">Avg Response Time:</span>
              <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                {rangeData.avgResponse}
              </p>
            </div>
            <div>
              <span className="text-[#7B8497]">Manual Equivalent:</span>
              <p className="text-sm font-bold text-[#7B8497] mt-0.5">~4.2 hrs / day</p>
            </div>
            <div>
              <span className="text-[#7B8497]">Speed Advantage:</span>
              <p className="text-sm font-bold text-purple-600 dark:text-purple-400 mt-0.5">
                18x faster with AI
              </p>
            </div>
          </div>
        </div>

        {/* Right: Category-wise Distribution Donut Chart (1 col) */}
        <div className="card-white p-5 space-y-4">
          <div>
            <h2 className="text-sm font-bold text-[#1E293B] dark:text-white flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-[#F97316]" />
              <span>Category Distribution</span>
            </h2>
            <p className="text-xs text-[#7B8497]">
              Classification across Work, College, Client, etc.
            </p>
          </div>

          <div className="h-44 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={CATEGORIES}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                >
                  {CATEGORIES.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomPieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Category breakdown rows */}
          <div className="space-y-2 pt-2 border-t border-[#E5EAF2] dark:border-[#334155]">
            {CATEGORIES.map(cat => (
              <div key={cat.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: cat.color }} />
                  <span className="font-medium text-[#1E293B] dark:text-white">{cat.name}</span>
                </div>
                <div className="flex items-center gap-2 text-[#7B8497]">
                  <span>{cat.count} emails</span>
                  <span className="font-bold text-[#1E293B] dark:text-white min-w-8 text-right">
                    {cat.value}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          SECTION D & E: Tasks & Calendar Integration (Combined Row)
      ───────────────────────────────────────────────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SECTION D: Tasks & Deadlines */}
        <div className="card-white p-5 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-[#E5EAF2] dark:border-[#334155]">
            <div>
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white flex items-center gap-2">
                <CheckSquare className="w-4 h-4 text-emerald-500" />
                <span>Tasks & Deadlines Extracted by AI</span>
              </h2>
              <p className="text-xs text-[#7B8497]">
                Action items identified from emails with priority tagging
              </p>
            </div>
            <button
              onClick={() => setCurrentPage('tasks')}
              className="text-xs font-semibold text-[#4169E1] hover:underline flex items-center gap-1"
            >
              <span>Manage in Tasks</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>

          {/* Task Status Overview Pills */}
          <div className="grid grid-cols-4 gap-2">
            <div className="p-2.5 rounded-xl bg-[#F8FAFC] dark:bg-[#162032] border border-[#E5EAF2] dark:border-[#334155] text-center">
              <span className="text-[10px] text-[#7B8497] font-medium">Upcoming</span>
              <p className="text-base font-bold text-[#4169E1] mt-0.5">{tasks.length}</p>
            </div>
            <div className="p-2.5 rounded-xl bg-[#F8FAFC] dark:bg-[#162032] border border-[#E5EAF2] dark:border-[#334155] text-center">
              <span className="text-[10px] text-[#7B8497] font-medium">Completed</span>
              <p className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">{completedTasks}</p>
            </div>
            <div className="p-2.5 rounded-xl bg-[#F8FAFC] dark:bg-[#162032] border border-[#E5EAF2] dark:border-[#334155] text-center">
              <span className="text-[10px] text-[#7B8497] font-medium">Pending</span>
              <p className="text-base font-bold text-amber-500 mt-0.5">{pendingTasks}</p>
            </div>
            <div className="p-2.5 rounded-xl bg-[#F8FAFC] dark:bg-[#162032] border border-[#E5EAF2] dark:border-[#334155] text-center">
              <span className="text-[10px] text-[#7B8497] font-medium">Overdue</span>
              <p className="text-base font-bold text-red-500 mt-0.5">{overdueTasks}</p>
            </div>
          </div>

          {/* Priority Breakdown Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-[#7B8497]">
              <span>Priority Breakdown:</span>
              <span className="font-medium text-[#1E293B] dark:text-white">
                {highPriorityTasks} High · {mediumPriorityTasks} Med · {lowPriorityTasks} Low
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-[#E5EAF2] dark:bg-[#334155] flex overflow-hidden">
              <div className="bg-red-500 h-full" style={{ width: '25%' }} title="High Priority" />
              <div className="bg-amber-400 h-full" style={{ width: '50%' }} title="Medium Priority" />
              <div className="bg-emerald-500 h-full" style={{ width: '25%' }} title="Low Priority" />
            </div>
          </div>

          {/* Interactive Task List */}
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {tasks.map(task => {
              const priorityColors = {
                high: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300 border-red-200 dark:border-red-900',
                medium: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border-amber-200 dark:border-amber-900',
                low: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900',
              };

              return (
                <div
                  key={task.id}
                  className={`flex items-start gap-3 p-3 rounded-xl border border-[#E5EAF2] dark:border-[#334155] transition-all ${
                    task.done ? 'bg-[#F8FAFC] dark:bg-[#162032] opacity-60' : 'bg-white dark:bg-[#1E293B]'
                  }`}
                >
                  <button
                    onClick={() => {
                      toggleTask(task.id);
                      toast.success(task.done ? 'Task marked pending' : 'Task completed!');
                    }}
                    className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center border transition-colors shrink-0 ${
                      task.done
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : 'border-[#7B8497] hover:border-[#4169E1]'
                    }`}
                  >
                    {task.done && <Check className="w-3 h-3" />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-semibold ${task.done ? 'line-through text-[#7B8497]' : 'text-[#1E293B] dark:text-white'}`}>
                      {task.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-[#7B8497]">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {task.dueDate}
                      </span>
                    </div>
                  </div>

                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border shrink-0 ${priorityColors[task.priority] || priorityColors.medium}`}>
                    {task.priority.toUpperCase()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* SECTION E: Calendar Reports & Smart Scheduling */}
        <div className="card-white p-5 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-[#E5EAF2] dark:border-[#334155]">
            <div>
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#4169E1]" />
                <span>Calendar Reports & Meeting Sync</span>
              </h2>
              <p className="text-xs text-[#7B8497]">
                AI-detected meeting invitations and synchronization status
              </p>
            </div>
            <button
              onClick={() => setCurrentPage('calendar')}
              className="text-xs font-semibold text-[#4169E1] hover:underline flex items-center gap-1"
            >
              <span>View Full Calendar</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>

          {/* AI Meeting Detection Banner */}
          <div className="p-3 rounded-xl bg-[#E8EEFF] dark:bg-[#4169E1]/15 border border-[#4169E1]/30 flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#4169E1] shrink-0" />
              <span className="text-[#1E293B] dark:text-[#E2E8F0]">
                <strong>3 meeting invites</strong> detected automatically by AI in your inbox
              </span>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#4169E1] text-white shrink-0">
              Auto-Synced
            </span>
          </div>

          {/* Upcoming Meetings List */}
          <div className="space-y-2.5">
            {MEETINGS.map(m => {
              const isAdded = addedMeetings.has(m.id);
              return (
                <div
                  key={m.id}
                  className="p-3.5 rounded-xl border border-[#E5EAF2] dark:border-[#334155] bg-white dark:bg-[#1E293B] flex items-center justify-between gap-3"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-bold text-[#1E293B] dark:text-white truncate">
                        {m.title}
                      </p>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-[#4169E1] border border-blue-200 dark:border-blue-900">
                        {m.platform}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-[#7B8497]">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {m.time}
                      </span>
                      <span className="truncate hidden sm:inline">
                        From: {m.detectedFrom}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleAddCalendar(m.id, m.title)}
                    className={`btn text-xs px-3 py-1.5 shrink-0 ${
                      isAdded ? 'btn-secondary text-emerald-600 dark:text-emerald-400' : 'btn-primary'
                    }`}
                  >
                    {isAdded ? (
                      <>
                        <Check className="w-3 h-3" />
                        <span>Added</span>
                      </>
                    ) : (
                      <>
                        <Calendar className="w-3 h-3" />
                        <span>Add</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>

          {/* Smart Notification Toggles */}
          <div className="p-3.5 rounded-xl border border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#162032] space-y-2.5">
            <span className="text-xs font-bold text-[#1E293B] dark:text-white block">
              Smart Notification Preferences
            </span>
            <div className="flex items-center justify-between gap-3 flex-wrap text-xs text-[#7B8497]">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={notifChannels.email}
                  onChange={e => {
                    setNotifChannels(p => ({ ...p, email: e.target.checked }));
                    toast.success(`Email alerts ${e.target.checked ? 'enabled' : 'disabled'}`);
                  }}
                  className="rounded text-[#4169E1] focus:ring-[#4169E1]"
                />
                <span className="text-[#1E293B] dark:text-white">Email Notifications</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={notifChannels.browser}
                  onChange={e => {
                    setNotifChannels(p => ({ ...p, browser: e.target.checked }));
                    toast.success(`Browser push ${e.target.checked ? 'enabled' : 'disabled'}`);
                  }}
                  className="rounded text-[#4169E1] focus:ring-[#4169E1]"
                />
                <span className="text-[#1E293B] dark:text-white">Browser Push</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={notifChannels.mobile}
                  onChange={e => {
                    setNotifChannels(p => ({ ...p, mobile: e.target.checked }));
                    toast.success(`Mobile push ${e.target.checked ? 'enabled' : 'disabled'}`);
                  }}
                  className="rounded text-[#4169E1] focus:ring-[#4169E1]"
                />
                <span className="text-[#1E293B] dark:text-white">Mobile Sync</span>
              </label>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
