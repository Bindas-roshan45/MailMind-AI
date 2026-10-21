import { useState } from 'react';
import {
  CheckSquare, Plus, Calendar, Clock, Trash2, ArrowLeft,
  CheckCircle2, AlertTriangle, Mail, Search, Check,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { EmptyState } from '../ui';
import toast from 'react-hot-toast';

export default function TasksPage() {
  const {
    tasks, toggleTask, addTask, deleteTask,
    setCurrentPage, setSelectedEmail, emails,
  } = useApp();

  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDueDate, setNewDueDate] = useState('Today');
  const [newPriority, setNewPriority] = useState('medium');
  const [newEmailId, setNewEmailId] = useState('');

  const handleCreateTask = (e) => {
    e.preventDefault();
    if (!newTitle.trim()) {
      toast.error('Please enter a task title');
      return;
    }
    addTask({
      title: newTitle.trim(),
      dueDate: newDueDate || 'Today',
      priority: newPriority,
      emailId: newEmailId || null,
    });
    setNewTitle('');
    setNewDueDate('Today');
    setNewPriority('medium');
    setNewEmailId('');
    setShowAddModal(false);
    toast.success('Task created successfully');
  };

  const handleEmailClick = (emailId) => {
    const target = emails.find(e => e.id === emailId);
    if (target) {
      setSelectedEmail(target);
      setCurrentPage('inbox');
    }
  };

  const filteredTasks = tasks.filter(t => {
    if (search && !t.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (filter === 'pending') return !t.done;
    if (filter === 'completed') return t.done;
    if (filter === 'high') return t.priority === 'high';
    if (filter === 'today') return t.dueDate?.toLowerCase().includes('today');
    return true;
  });

  const totalCount = tasks.length;
  const pendingCount = tasks.filter(t => !t.done).length;
  const completedCount = tasks.filter(t => t.done).length;
  const highPriorityCount = tasks.filter(t => t.priority === 'high' && !t.done).length;

  const priorityStyles = {
    high: 'text-red-700 bg-red-50 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900/40',
    medium: 'text-amber-700 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/40',
    low: 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900/40',
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
            <h1 className="text-xl font-bold text-[#1E293B] dark:text-white">Upcoming Tasks & Follow-ups</h1>
            <p className="text-xs text-[#7B8497] mt-0.5">
              Action items extracted automatically by AI or created manually
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5 shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Task</span>
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="card-white p-3.5 sm:p-4">
          <div className="flex items-center justify-between text-[#7B8497] mb-1">
            <span className="text-xs font-medium">Total Tasks</span>
            <CheckSquare className="w-4 h-4 text-[#4169E1]" />
          </div>
          <p className="text-2xl font-bold text-[#1E293B] dark:text-white">{totalCount}</p>
        </div>

        <div className="card-white p-3.5 sm:p-4">
          <div className="flex items-center justify-between text-[#7B8497] mb-1">
            <span className="text-xs font-medium">Pending</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{pendingCount}</p>
        </div>

        <div className="card-white p-3.5 sm:p-4">
          <div className="flex items-center justify-between text-[#7B8497] mb-1">
            <span className="text-xs font-medium">Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{completedCount}</p>
        </div>

        <div className="card-white p-3.5 sm:p-4">
          <div className="flex items-center justify-between text-[#7B8497] mb-1">
            <span className="text-xs font-medium">High Priority</span>
            <AlertTriangle className="w-4 h-4 text-red-500" />
          </div>
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">{highPriorityCount}</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card-white p-3 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1 sm:pb-0">
          {[
            { id: 'all',       label: 'All Tasks',  count: totalCount },
            { id: 'pending',   label: 'Pending',    count: pendingCount },
            { id: 'completed', label: 'Completed',  count: completedCount },
            { id: 'high',      label: 'High Priority', count: highPriorityCount },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
                filter === tab.id
                  ? 'bg-[#4169E1] text-white font-semibold shadow-xs'
                  : 'text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white hover:bg-[#F5F7FC] dark:hover:bg-[#28384E]'
              }`}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#7B8497]" />
          <input
            type="text"
            placeholder="Search tasks..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#F5F7FC] dark:bg-[#0F172A] border border-[#E5EAF2] dark:border-[#334155] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[#1E293B] dark:text-white placeholder-[#7B8497] outline-none focus:border-[#4169E1]"
          />
        </div>
      </div>

      {/* Task List */}
      <div className="card-white overflow-hidden divide-y divide-[#E5EAF2] dark:divide-[#334155]">
        {filteredTasks.length === 0 ? (
          <EmptyState
            icon={CheckSquare}
            title="No tasks match your filter"
            description="All caught up! Add a new task or switch to another filter tab."
          />
        ) : (
          filteredTasks.map(task => {
            const linkedEmail = task.emailId ? emails.find(e => e.id === task.emailId) : null;

            return (
              <div
                key={task.id}
                className="p-4 flex items-center justify-between gap-3 hover:bg-[#FBFDFF] dark:hover:bg-[#1E2D44] transition-colors group"
              >
                <div className="flex items-center gap-3.5 min-w-0 flex-1">
                  <button
                    onClick={() => toggleTask(task.id)}
                    className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 transition-colors ${
                      task.done
                        ? 'bg-[#4169E1] border-[#4169E1] text-white'
                        : 'border-[#CBD5E1] dark:border-slate-600 hover:border-[#4169E1] bg-white dark:bg-[#0F172A]'
                    }`}
                    aria-label={task.done ? 'Mark pending' : 'Mark done'}
                  >
                    {task.done && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                  </button>

                  <div className="min-w-0 flex-1">
                    <p
                      className={`text-sm ${
                        task.done
                          ? 'line-through text-[#94A3B8] dark:text-[#64748B]'
                          : 'font-medium text-[#1E293B] dark:text-white'
                      }`}
                    >
                      {task.title}
                    </p>

                    <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                      <span className="flex items-center gap-1 text-[11px] text-[#7B8497]">
                        <Calendar className="w-3 h-3 text-[#4169E1]" />
                        <span>{task.dueDate}</span>
                      </span>

                      {linkedEmail && (
                        <button
                          onClick={() => handleEmailClick(linkedEmail.id)}
                          className="flex items-center gap-1 text-[11px] text-[#4169E1] hover:underline bg-[#E8EEFF] dark:bg-[#4169E1]/20 px-2 py-0.5 rounded-md"
                          title="View related email"
                        >
                          <Mail className="w-3 h-3" />
                          <span className="truncate max-w-[200px]">{linkedEmail.subject}</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded border uppercase tracking-wider ${
                      priorityStyles[task.priority] || priorityStyles.medium
                    }`}
                  >
                    {task.priority}
                  </span>

                  <button
                    onClick={() => {
                      deleteTask(task.id);
                      toast.success('Task deleted');
                    }}
                    className="p-1.5 rounded-md text-[#7B8497] hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors opacity-0 group-hover:opacity-100"
                    title="Delete task"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Add Task Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-modal w-full max-w-md overflow-hidden animate-slide-up">
            <div className="px-5 py-3.5 border-b border-[#E5EAF2] dark:border-[#334155] flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#1E293B] dark:text-white">Create New Task</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#7B8497] mb-1">Task Title</label>
                <input
                  type="text"
                  autoFocus
                  placeholder="e.g. Follow up on Q4 Budget Proposal"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="input-minimal"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#7B8497] mb-1">Due Date</label>
                  <input
                    type="text"
                    placeholder="e.g. Tomorrow, 5 PM"
                    value={newDueDate}
                    onChange={e => setNewDueDate(e.target.value)}
                    className="input-minimal"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7B8497] mb-1">Priority</label>
                  <select
                    value={newPriority}
                    onChange={e => setNewPriority(e.target.value)}
                    className="input-minimal cursor-pointer"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#7B8497] mb-1">Link to Email (Optional)</label>
                <select
                  value={newEmailId}
                  onChange={e => setNewEmailId(e.target.value)}
                  className="input-minimal cursor-pointer"
                >
                  <option value="">None (Independent task)</option>
                  {emails.slice(0, 10).map(e => (
                    <option key={e.id} value={e.id}>
                      {e.subject} — {e.from.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E5EAF2] dark:border-[#334155]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary text-xs">
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
