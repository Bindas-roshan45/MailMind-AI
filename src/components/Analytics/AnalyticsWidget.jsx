import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, ArrowUpRight } from 'lucide-react';
import { useApp } from '../../context/AppContext';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-slate-800 p-2 text-xs rounded-lg border border-[#E5EAF2] dark:border-slate-700 shadow-card">
      <p className="font-semibold text-[#1E293B] dark:text-white mb-1">{label}</p>
      <p className="text-[#4169E1]">Received: {payload[0]?.value}</p>
      <p className="text-[#7B8497]">Replied: {payload[1]?.value}</p>
    </div>
  );
};

export default function AnalyticsWidget() {
  const { setCurrentPage, emails, folderCounts } = useApp();

  const totalReceived = folderCounts?.inbox ?? emails.length;
  const pending = emails.filter(e => e.requiresReply).length;
  const totalReplied = folderCounts?.sent ?? emails.filter(e => !e.requiresReply).length;

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const dayCounts = { Mon: 0, Tue: 0, Wed: 0, Thu: 0, Fri: 0, Sat: 0, Sun: 0 };
  const repliedCounts = { Mon: 0, Tue: 0, Wed: 0, Thu: 0, Fri: 0, Sat: 0, Sun: 0 };

  emails.forEach(e => {
    if (e.date) {
      const dayName = new Date(e.date).toLocaleDateString('en-US', { weekday: 'short' });
      if (dayCounts[dayName] !== undefined) {
        dayCounts[dayName] += 1;
        if (!e.requiresReply) repliedCounts[dayName] += 1;
      }
    }
  });

  const weeklyData = days.map(d => ({
    day: d,
    received: dayCounts[d],
    replied: repliedCounts[d],
  }));

  return (
    <div className="card-white p-4 h-full flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-[#E8EEFF] dark:bg-[#4169E1]/20 flex items-center justify-center text-[#4169E1] dark:text-[#93C5FD]">
            <TrendingUp className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-[#1E293B] dark:text-white">Email Activity</span>
          <span className="text-[10px] text-[#7B8497]">(Last 7 Days)</span>
        </div>

        <button
          onClick={() => setCurrentPage('analytics')}
          className="text-xs font-semibold text-[#4169E1] hover:underline flex items-center gap-0.5"
        >
          <span>View all</span>
          <ArrowUpRight className="w-3 h-3" />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 py-1 mb-2 border-y border-[#E5EAF2] dark:border-[#334155]">
        <div>
          <span className="text-[10px] text-[#7B8497] block">Received</span>
          <span className="text-sm font-bold text-[#1E293B] dark:text-white">{totalReceived}</span>
        </div>
        <div>
          <span className="text-[10px] text-[#7B8497] block">Replied</span>
          <span className="text-sm font-bold text-[#4169E1]">{totalReplied}</span>
        </div>
        <div>
          <span className="text-[10px] text-[#7B8497] block">Pending</span>
          <span className="text-sm font-bold text-amber-600">{pending}</span>
        </div>
      </div>

      <div className="h-28 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={weeklyData} barSize={6} barGap={3}>
            <XAxis
              dataKey="day"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#7B8497', fontSize: 10 }}
            />
            <YAxis hide />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(65, 105, 225, 0.05)' }} />
            <Bar dataKey="received" fill="#4169E1" radius={[2, 2, 0, 0]} />
            <Bar dataKey="replied"  fill="#CBD5E1" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
