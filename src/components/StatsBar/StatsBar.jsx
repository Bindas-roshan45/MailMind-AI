import { Mail, MessageCircle, AlertTriangle, Briefcase, Sparkles } from 'lucide-react';
import { MOCK_ANALYTICS } from '../../data/mockData';
import { useApp } from '../../context/AppContext';

export default function StatsBar() {
  const { setActiveFilter, setActiveFolder, setCurrentPage } = useApp();

  const STATS = [
    {
      id: 'total',
      label: 'Total Emails',
      value: MOCK_ANALYTICS.totalReceived,
      icon: Mail,
      onClick: () => { setCurrentPage('inbox'); setActiveFilter('all'); },
    },
    {
      id: 'pending',
      label: 'Needs Reply',
      value: MOCK_ANALYTICS.pending,
      icon: MessageCircle,
      onClick: () => { setCurrentPage('inbox'); setActiveFilter('needs_reply'); },
    },
    {
      id: 'urgent',
      label: 'Urgent Priority',
      value: MOCK_ANALYTICS.urgent,
      icon: AlertTriangle,
      onClick: () => { setCurrentPage('inbox'); setActiveFilter('important'); },
    },
    {
      id: 'work',
      label: 'Work Inquiries',
      value: 18,
      icon: Briefcase,
      onClick: () => { setCurrentPage('inbox'); setActiveFolder('inbox'); },
    },
  ];

  return (
    <div className="px-4 py-3 border-b border-[#E5EAF2] dark:border-[#334155] bg-transparent">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {STATS.map(stat => {
          const Icon = stat.icon;
          return (
            <button
              key={stat.id}
              onClick={stat.onClick}
              className="card-white p-3 flex items-center justify-between text-left hover:border-[#D1D9E7] dark:hover:border-[#475569] transition-all group cursor-pointer"
            >
              <div>
                <p className="text-[11px] font-medium text-[#7B8497] dark:text-[#94A3B8]">{stat.label}</p>
                <p className="text-xl font-bold text-[#1E293B] dark:text-white mt-0.5 tracking-tight">{stat.value}</p>
              </div>
              <div className="w-8 h-8 rounded-lg bg-[#E8EEFF] dark:bg-[#4169E1]/15 text-[#4169E1] dark:text-[#93C5FD] flex items-center justify-center shrink-0">
                <Icon className="w-4 h-4" />
              </div>
            </button>
          );
        })}

        {/* AI Agent Status Card */}
        <div className="card-white p-3 col-span-2 sm:col-span-1 lg:col-span-1 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <p className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">AI Agent Active</p>
            </div>
            <p className="text-xs font-semibold text-[#1E293B] dark:text-white mt-0.5">Auto-monitoring</p>
            <p className="text-[10px] text-[#7B8497] dark:text-[#94A3B8]">Checked 2m ago</p>
          </div>
          <div className="w-8 h-8 rounded-lg bg-[#E8EEFF] dark:bg-[#4169E1]/15 text-[#4169E1] dark:text-[#93C5FD] flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>
  );
}
