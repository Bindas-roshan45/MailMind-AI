import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { MOCK_ANALYTICS } from '../../data/mockData';
import { TrendingUp, Clock, CheckCircle2, Zap, ArrowLeft, Download } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function AnalyticsPage() {
  const { setCurrentPage } = useApp();
  const { weeklyData, totalReceived, totalReplied } = MOCK_ANALYTICS;

  const PIE_DATA = [
    { name: 'Work', value: 38, color: '#4169E1' },
    { name: 'Client', value: 24, color: '#F97316' },
    { name: 'College', value: 18, color: '#22C55E' },
    { name: 'Promotions', value: 12, color: '#A855F7' },
    { name: 'Other', value: 8, color: '#64748B' },
  ];

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto p-4 sm:p-6 bg-[#F5F7FC] dark:bg-[#0F172A] space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentPage('inbox')}
            className="p-1.5 rounded-lg bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-[#1E293B] dark:text-white">Analytics & Performance</h1>
            <p className="text-xs text-[#7B8497] mt-0.5">Real-time metrics on inbox velocity and AI productivity</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="btn-secondary text-xs flex items-center gap-1.5">
            <Download className="w-3.5 h-3.5 text-[#7B8497]" />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Received (7d)', value: totalReceived, change: `${totalReplied} replied with AI`, icon: TrendingUp },
          { label: 'Avg Response Time', value: '18 mins', change: '4x faster with AI', icon: Clock },
          { label: 'AI Acceptance Rate', value: '94.2%', change: '34 replies generated', icon: Zap },
          { label: 'Weekly Time Saved', value: '5.4 hrs', change: 'Productivity boost', icon: CheckCircle2 },
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={idx} className="card-white p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[#7B8497]">{item.label}</span>
                <div className="w-8 h-8 rounded-lg bg-[#E8EEFF] dark:bg-[#4169E1]/20 text-[#4169E1] dark:text-[#93C5FD] flex items-center justify-center">
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <p className="text-2xl font-bold text-[#1E293B] dark:text-white mt-2">{item.value}</p>
              <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 mt-1 inline-block">
                {item.change}
              </span>
            </div>
          );
        })}
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly Traffic (2 cols) */}
        <div className="card-white p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#1E293B] dark:text-white">Email Traffic & Replies</h2>
              <p className="text-xs text-[#7B8497]">Comparison of inbound emails and outgoing replies</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-[#1E293B] dark:text-[#E2E8F0]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#4169E1]" /> Received
              </span>
              <span className="flex items-center gap-1.5 text-[#1E293B] dark:text-[#E2E8F0]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#CBD5E1]" /> Replied
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyData} barSize={12} barGap={6}>
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#7B8497', fontSize: 11 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#7B8497', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px solid #E5EAF2',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="received" fill="#4169E1" radius={[3, 3, 0, 0]} />
                <Bar dataKey="replied"  fill="#CBD5E1" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Breakdown (1 col) */}
        <div className="card-white p-5 space-y-4">
          <div>
            <h2 className="text-sm font-bold text-[#1E293B] dark:text-white">Email Categories</h2>
            <p className="text-xs text-[#7B8497]">Distribution by topic</p>
          </div>

          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={PIE_DATA} dataKey="value" innerRadius={42} outerRadius={68} paddingAngle={4}>
                  {PIE_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-2 pt-2 border-t border-[#E5EAF2] dark:border-[#334155]">
            {PIE_DATA.map(item => (
              <div key={item.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-[#334155] dark:text-[#CBD5E1]">{item.name}</span>
                </div>
                <span className="font-semibold text-[#1E293B] dark:text-white">{item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
