import {
  PenSquare, AlignLeft, Search, CheckSquare,
  Calendar, MessageCircle,
} from 'lucide-react';

const ACTIONS = [
  { icon: PenSquare,     label: 'Compose' },
  { icon: AlignLeft,     label: 'Summarize' },
  { icon: Search,        label: 'Find Email' },
  { icon: CheckSquare,   label: 'Create Task' },
  { icon: Calendar,      label: 'Schedule' },
  { icon: MessageCircle, label: 'AI Chat' },
];

export default function QuickActionsWidget() {
  return (
    <div className="glass-card p-4 rounded-xl h-full animate-fade-in">
      <p className="text-sm font-semibold text-white mb-3">Quick Actions</p>
      <div className="grid grid-cols-3 gap-2">
        {ACTIONS.map(action => {
          const Icon = action.icon;
          return (
            <button
              key={action.label}
              className="flex flex-col items-center gap-1.5 p-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.05] hover:border-blue-500/30 transition-all group"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-violet-500/10 flex items-center justify-center group-hover:from-blue-500/30 group-hover:to-violet-500/20 transition-all">
                <Icon className="w-4 h-4 text-blue-400 group-hover:text-blue-300" />
              </div>
              <span className="text-[10px] text-gray-500 group-hover:text-gray-300 transition-colors">{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
