import { useState } from 'react';
import { CheckSquare, Plus, Calendar, ArrowUpRight, Check } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function TasksWidget() {
  const { tasks, toggleTask, addTask, setCurrentPage } = useApp();
  const [newTitle, setNewTitle] = useState('');
  const [showInput, setShowInput] = useState(false);

  const handleAdd = (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    addTask({
      title: newTitle.trim(),
      dueDate: 'Today',
      priority: 'medium',
    });
    setNewTitle('');
    setShowInput(false);
  };

  const priorityColors = {
    high: 'text-red-600 bg-red-50 dark:bg-red-950/40 dark:text-red-300',
    medium: 'text-amber-600 bg-amber-50 dark:bg-amber-950/40 dark:text-amber-300',
    low: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 dark:text-emerald-300',
  };

  return (
    <div className="card-white p-4 h-full flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-[#E8EEFF] dark:bg-[#4169E1]/20 flex items-center justify-center text-[#4169E1] dark:text-[#93C5FD]">
            <CheckSquare className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-[#1E293B] dark:text-white">Upcoming Tasks</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowInput(prev => !prev)}
            className="p-1 rounded text-[#7B8497] hover:text-[#4169E1] transition-colors"
            title="Add task"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setCurrentPage('tasks')}
            className="text-xs font-semibold text-[#4169E1] hover:underline flex items-center gap-0.5"
          >
            <span>View all</span>
            <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {showInput && (
        <form onSubmit={handleAdd} className="mb-2">
          <input
            type="text"
            autoFocus
            placeholder="Type task and press Enter..."
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-[#F5F7FC] dark:bg-[#0F172A] outline-none focus:border-[#4169E1]"
          />
        </form>
      )}

      {/* Task list */}
      <div className="space-y-2 overflow-y-auto max-h-36 pr-1 flex-1">
        {tasks.slice(0, 4).map(task => (
          <div
            key={task.id}
            className="flex items-center justify-between gap-2 p-1.5 rounded-lg hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors group"
          >
            <div className="flex items-center gap-2.5 min-w-0 flex-1">
              <button
                type="button"
                onClick={() => toggleTask(task.id)}
                className={`w-4 h-4 rounded border transition-colors flex items-center justify-center shrink-0 ${
                  task.done
                    ? 'bg-[#4169E1] border-[#4169E1] text-white'
                    : 'border-[#CBD5E1] dark:border-slate-600 hover:border-[#4169E1]'
                }`}
              >
                {task.done && <Check className="w-3 h-3 stroke-[3]" />}
              </button>

              <div className="min-w-0">
                <p
                  className={`text-xs truncate ${
                    task.done
                      ? 'line-through text-[#7B8497]'
                      : 'font-medium text-[#1E293B] dark:text-[#E2E8F0]'
                  }`}
                >
                  {task.title}
                </p>
                <div className="flex items-center gap-1 text-[10px] text-[#7B8497]">
                  <Calendar className="w-2.5 h-2.5" />
                  <span>{task.dueDate}</span>
                </div>
              </div>
            </div>

            <span
              className={`text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase shrink-0 ${
                priorityColors[task.priority] || priorityColors.medium
              }`}
            >
              {task.priority}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
