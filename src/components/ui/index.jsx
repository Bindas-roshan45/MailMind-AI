import { CATEGORY_COLORS } from '../../data/mockData';

export function CategoryBadge({ category, size = 'sm' }) {
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS['Notification'];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md font-medium text-[11px] ${colors.bg} ${colors.text} ${
        size === 'xs' ? 'text-[10px] px-1.5 py-0.2' : ''
      }`}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colors.dot }} />
      {category}
    </span>
  );
}

export function UrgencyBadge({ urgency }) {
  const map = {
    urgent: 'bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-300 border border-red-200 dark:border-red-800/40',
    high:   'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800/40',
    medium: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800/40',
    low:    'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700',
  };
  if (!urgency || urgency === 'low') return null;
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${map[urgency]}`}>
      {urgency}
    </span>
  );
}

export function Avatar({ name = '', size = 'md', className = '' }) {
  const initials = name
    .split(' ')
    .filter(Boolean)
    .map(w => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || 'U';

  const sizes = {
    xs: 'w-6 h-6 text-[10px]',
    sm: 'w-7 h-7 text-xs',
    md: 'w-9 h-9 text-xs',
    lg: 'w-10 h-10 text-sm',
    xl: 'w-12 h-12 text-base',
  };

  return (
    <div
      className={`${sizes[size]} rounded-full bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD] font-semibold flex items-center justify-center shrink-0 border border-[#E5EAF2] dark:border-[#334155] ${className}`}
    >
      {initials}
    </div>
  );
}

export function PriorityDot({ priority }) {
  const colors = {
    high: 'bg-red-500',
    medium: 'bg-amber-500',
    low: 'bg-emerald-500',
  };
  return <span className={`w-2 h-2 rounded-full ${colors[priority] || 'bg-slate-400'} shrink-0`} />;
}

export function Spinner({ size = 'sm' }) {
  const s = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' };
  return (
    <div className={`${s[size]} border-2 border-[#E5EAF2] border-t-[#4169E1] rounded-full animate-spin`} />
  );
}

export function MockDataBanner() {
  return (
    <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/40 rounded-lg text-xs text-amber-700 dark:text-amber-400">
      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
      <span className="font-medium">Demo Mode</span>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 gap-2.5 text-center">
      {Icon && (
        <div className="w-12 h-12 rounded-xl bg-[#F5F7FC] dark:bg-slate-800 flex items-center justify-center text-[#7B8497] dark:text-slate-400 mb-1 border border-[#E5EAF2] dark:border-slate-700">
          <Icon className="w-6 h-6" />
        </div>
      )}
      <p className="text-[#1E293B] dark:text-[#F8FAFC] font-semibold text-sm">{title}</p>
      {description && <p className="text-[#7B8497] dark:text-[#94A3B8] text-xs max-w-xs">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
