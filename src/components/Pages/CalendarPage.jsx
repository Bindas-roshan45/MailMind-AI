import { useState, useEffect } from 'react';
import {
  Calendar as CalendarIcon, ChevronLeft, ChevronRight,
  Clock, Plus, ArrowLeft, Video, CheckCircle2, Mail, Trash2,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

const INITIAL_EVENTS = [
  { id: 'ev-1', title: 'Website Project Inquiry Sync', date: 14, time: '10:00 AM - 10:30 AM', category: 'Client', type: 'Google Meet', emailSubject: 'Website Project Inquiry' },
  { id: 'ev-2', title: 'Q3 Strategy & Performance Review', date: 16, time: '2:00 PM - 3:00 PM', category: 'Work', type: 'Conference Room B', emailSubject: 'Q3 Product Strategy Review' },
  { id: 'ev-3', title: 'College Project Submission Deadline', date: 20, time: '11:59 PM', category: 'College', type: 'Portal Submission', emailSubject: 'Final Project Submission Guidelines' },
  { id: 'ev-4', title: 'Weekly Sprint Standup', date: 13, time: '11:00 AM - 11:30 AM', category: 'Work', type: 'Google Meet', emailSubject: 'Weekly Sync Agenda' },
  { id: 'ev-5', title: 'Contract Renewal Discussion', date: 24, time: '4:00 PM - 4:45 PM', category: 'Client', type: 'Zoom Call', emailSubject: 'Follow-up on Agreement' },
];

export default function CalendarPage() {
  const { setCurrentPage } = useApp();
  const [selectedDay, setSelectedDay] = useState(13);
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newTime, setNewTime] = useState('11:00 AM');
  const [newCategory, setNewCategory] = useState('Work');

  useEffect(() => {
    async function loadCalendarEvents() {
      try {
        const res = await api.calendar.list();
        if (res?.success && Array.isArray(res.data) && res.data.length > 0) {
          const mapped = res.data.map(e => ({
            id: e.id,
            title: e.title,
            date: e.start_time ? new Date(e.start_time).getDate() : 13,
            time: e.start_time ? new Date(e.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '10:00 AM',
            category: 'Work',
            type: e.location || 'Calendar Event',
          }));
          setEvents(mapped);
        }
      } catch {
        // Keeps INITIAL_EVENTS
      }
    }
    loadCalendarEvents();
  }, []);

  const daysInMonth = 31;
  const startDayOffset = 4; // October 2026 starts on Thursday

  const handleAddEvent = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    const newEv = {
      id: `ev-${Date.now()}`,
      title: newTitle.trim(),
      date: selectedDay,
      time: newTime || '12:00 PM',
      category: newCategory,
      type: 'Calendar Event',
    };

    setEvents(prev => [...prev, newEv]);
    setNewTitle('');
    setShowAddEvent(false);
    toast.success(`Event added for Oct ${selectedDay}`);

    try {
      const startTime = new Date(2026, 9, selectedDay, 10, 0, 0).toISOString();
      const endTime = new Date(2026, 9, selectedDay, 11, 0, 0).toISOString();
      await api.calendar.create({
        title: newEv.title,
        start_time: startTime,
        end_time: endTime,
        location: newCategory === 'Client' ? 'Zoom Call' : 'Google Meet',
      });
    } catch {
      // Local fallback active
    }
  };

  const handleDeleteEvent = async (id) => {
    setEvents(prev => prev.filter(e => e.id !== id));
    toast.success('Event removed');
    try {
      await api.calendar.delete(id);
    } catch {
      // Local state updated
    }
  };

  const selectedDayEvents = events.filter(e => e.date === selectedDay);

  const categoryBadgeColors = {
    Work: 'bg-[#E8EEFF] text-[#4169E1] border-[#4169E1]/30 dark:bg-[#4169E1]/20 dark:text-[#93C5FD]',
    Client: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300',
    College: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300',
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto p-4 sm:p-6 bg-[#F5F7FC] dark:bg-[#0F172A] space-y-6">
      {/* Header */}
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
            <h1 className="text-xl font-bold text-[#1E293B] dark:text-white">Email & AI Smart Calendar</h1>
            <p className="text-xs text-[#7B8497] mt-0.5">
              Scheduled meetings, deadlines and touchpoints detected in your inbox
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowAddEvent(true)}
          className="btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5 shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Add Event</span>
        </button>
      </div>

      {/* Main Grid: Calendar on Left, Selected Day Agenda on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card-white p-5 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarIcon className="w-5 h-5 text-[#4169E1]" />
              <h2 className="text-base font-bold text-[#1E293B] dark:text-white">October 2026</h2>
            </div>
            <div className="flex items-center gap-1 text-[#7B8497]">
              <button className="p-1 rounded-md hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setSelectedDay(13)}
                className="px-2 py-1 text-xs font-semibold hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] rounded-md text-[#4169E1]"
              >
                Today
              </button>
              <button className="p-1 rounded-md hover:bg-[#F5F7FC] dark:hover:bg-[#28384E] transition-colors">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center font-semibold text-xs text-[#7B8497] pb-1 border-b border-[#E5EAF2] dark:border-[#334155]">
            <span>Sun</span>
            <span>Mon</span>
            <span>Tue</span>
            <span>Wed</span>
            <span>Thu</span>
            <span>Fri</span>
            <span>Sat</span>
          </div>

          <div className="grid grid-cols-7 gap-1.5">
            {Array.from({ length: startDayOffset }).map((_, idx) => (
              <div key={`offset-${idx}`} className="h-16 sm:h-20 rounded-lg bg-[#F8FAFC]/50 dark:bg-[#1E293B]/30" />
            ))}

            {Array.from({ length: daysInMonth }).map((_, idx) => {
              const day = idx + 1;
              const isSelected = selectedDay === day;
              const isToday = day === 13;
              const dayEvents = events.filter(e => e.date === day);

              return (
                <div
                  key={day}
                  onClick={() => setSelectedDay(day)}
                  className={`h-16 sm:h-20 p-1.5 rounded-lg border transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'border-[#4169E1] bg-[#E8EEFF]/40 dark:bg-[#4169E1]/15 ring-1 ring-[#4169E1]'
                      : isToday
                      ? 'border-[#4169E1]/50 bg-white dark:bg-[#1E293B] shadow-xs'
                      : 'border-[#E5EAF2] dark:border-[#334155] bg-white dark:bg-[#1E293B] hover:border-[#CBD5E1]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-semibold inline-flex items-center justify-center w-5 h-5 rounded-full ${
                        isToday
                          ? 'bg-[#4169E1] text-white'
                          : isSelected
                          ? 'text-[#4169E1] font-bold'
                          : 'text-[#1E293B] dark:text-[#E2E8F0]'
                      }`}
                    >
                      {day}
                    </span>
                    {dayEvents.length > 0 && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#4169E1]" />
                    )}
                  </div>

                  <div className="space-y-0.5 overflow-hidden">
                    {dayEvents.slice(0, 1).map(ev => (
                      <div
                        key={ev.id}
                        className="text-[9px] truncate px-1 py-0.2 rounded bg-[#E8EEFF] text-[#4169E1] dark:bg-[#4169E1]/20 dark:text-[#93C5FD] font-medium"
                      >
                        {ev.title}
                      </div>
                    ))}
                    {dayEvents.length > 1 && (
                      <span className="text-[8px] text-[#7B8497] block leading-none">
                        +{dayEvents.length - 1} more
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-4">
          <div className="card-white p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#E5EAF2] dark:border-[#334155] pb-3">
              <div>
                <h3 className="text-sm font-bold text-[#1E293B] dark:text-white">
                  Schedule for Oct {selectedDay}, 2026
                </h3>
                <p className="text-xs text-[#7B8497] mt-0.5">
                  {selectedDayEvents.length} {selectedDayEvents.length === 1 ? 'event scheduled' : 'events scheduled'}
                </p>
              </div>
              <button
                onClick={() => setShowAddEvent(true)}
                className="p-1 rounded text-[#4169E1] hover:bg-[#E8EEFF] dark:hover:bg-[#4169E1]/20 transition-colors"
                title="Add event for this day"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              {selectedDayEvents.length === 0 ? (
                <div className="py-8 text-center text-xs text-[#7B8497]">
                  No events or meetings scheduled for this date.
                </div>
              ) : (
                selectedDayEvents.map(ev => (
                  <div
                    key={ev.id}
                    className="p-3 rounded-lg border border-[#E5EAF2] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#131E31] space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-[#1E293B] dark:text-white line-clamp-1">
                        {ev.title}
                      </span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded border uppercase ${
                            categoryBadgeColors[ev.category] || categoryBadgeColors.Work
                          }`}
                        >
                          {ev.category}
                        </span>
                        <button
                          onClick={() => handleDeleteEvent(ev.id)}
                          className="p-1 rounded text-[#7B8497] hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                          title="Delete event"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-[#7B8497]">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-[#4169E1]" />
                        <span>{ev.time}</span>
                      </span>
                      <span className="flex items-center gap-1">
                        <Video className="w-3.5 h-3.5" />
                        <span>{ev.type}</span>
                      </span>
                    </div>

                    {ev.emailSubject && (
                      <div className="pt-1 border-t border-[#E5EAF2] dark:border-[#334155] flex items-center gap-1 text-[11px] text-[#4169E1]">
                        <Mail className="w-3 h-3 shrink-0" />
                        <span className="truncate">Extracted from: "{ev.emailSubject}"</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="card-white p-4 space-y-2 bg-gradient-to-br from-white to-[#F5F7FC] dark:from-[#1E293B] dark:to-[#131E31]">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <h4 className="text-xs font-bold text-[#1E293B] dark:text-white">Calendar AI Sync Active</h4>
            </div>
            <p className="text-xs text-[#7B8497] leading-relaxed">
              When emails contain dates, appointments or deadlines, MailMind AI automatically parses and adds them to your calendar.
            </p>
          </div>
        </div>
      </div>

      {showAddEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="bg-white dark:bg-[#1E293B] border border-[#E5EAF2] dark:border-[#334155] rounded-xl shadow-modal w-full max-w-md overflow-hidden animate-slide-up">
            <div className="px-5 py-3.5 border-b border-[#E5EAF2] dark:border-[#334155] flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#1E293B] dark:text-white">Add Event for Oct {selectedDay}</h3>
              <button
                onClick={() => setShowAddEvent(false)}
                className="text-[#7B8497] hover:text-[#1E293B] dark:hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddEvent} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#7B8497] mb-1">Event Title</label>
                <input
                  type="text"
                  autoFocus
                  placeholder="e.g. Design review with Client"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="input-minimal"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#7B8497] mb-1">Time</label>
                  <input
                    type="text"
                    placeholder="e.g. 3:00 PM - 4:00 PM"
                    value={newTime}
                    onChange={e => setNewTime(e.target.value)}
                    className="input-minimal"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#7B8497] mb-1">Category</label>
                  <select
                    value={newCategory}
                    onChange={e => setNewCategory(e.target.value)}
                    className="input-minimal cursor-pointer"
                  >
                    <option value="Work">Work</option>
                    <option value="Client">Client</option>
                    <option value="College">College</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E5EAF2] dark:border-[#334155]">
                <button
                  type="button"
                  onClick={() => setShowAddEvent(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary text-xs">
                  Save Event
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
