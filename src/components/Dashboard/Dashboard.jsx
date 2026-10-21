import { useState } from 'react';
import Sidebar from '../Sidebar/Sidebar';
import Topbar from '../Topbar/Topbar';
import StatsBar from '../StatsBar/StatsBar';
import EmailList from '../EmailList/EmailList';
import EmailDetail from '../EmailDetail/EmailDetail';
import ComposeModal from '../Compose/ComposeModal';
import PushNotificationToast from '../Notifications/PushNotificationToast';

import AnalyticsPage from '../Pages/AnalyticsPage';
import TasksPage from '../Pages/TasksPage';
import ReportsPage from '../Pages/ReportsPage';
import CalendarPage from '../Pages/CalendarPage';
import SettingsPage from '../Pages/SettingsPage';

import { useApp } from '../../context/AppContext';

export default function Dashboard() {
  const { currentPage } = useApp();
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-[#F5F7FC] dark:bg-[#0F172A] text-[#1E293B] dark:text-[#F8FAFC] font-sans">
      {/* ── Left: Compact Navigation Sidebar ── */}
      <Sidebar />

      {/* ── Main Content Area ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* ── Top: Search, Notifications, Profile, Gmail Status ── */}
        <Topbar />

        {/* ── Dedicated Full Pages ── */}
        {currentPage === 'analytics' && <AnalyticsPage />}
        {currentPage === 'tasks' && <TasksPage />}
        {currentPage === 'reports' && <ReportsPage />}
        {currentPage === 'calendar' && <CalendarPage />}
        {currentPage === 'settings' && <SettingsPage />}

        {/* ── Main Inbox Dashboard ── */}
        {currentPage === 'inbox' && (
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Top Stat Strip: Email statistics with minimal cards */}
            <StatsBar />

            {/* Core Workspace: Center Inbox & Reading Panel */}
            <div className="flex-1 flex overflow-hidden">
              {/* Column 1: Clean Inbox list (responsive on mobile) */}
              <div
                className={`w-full md:w-80 lg:w-96 shrink-0 h-full ${
                  mobileDetailOpen ? 'hidden md:flex' : 'flex'
                }`}
              >
                <EmailList onSelectMobile={() => setMobileDetailOpen(true)} />
              </div>

              {/* Column 2: Email Reading Panel & Right Contextual Suggestions */}
              <div
                className={`flex-1 flex flex-col min-w-0 overflow-hidden ${
                  !mobileDetailOpen ? 'hidden md:flex' : 'flex'
                }`}
              >
                {/* Email reading panel & contextual AI suggestions — full height */}
                <div className="flex-1 flex overflow-hidden">
                  <EmailDetail onBack={() => setMobileDetailOpen(false)} />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Compose Email Modal ── */}
      <ComposeModal />

      {/* ── Push Notification Toast ── */}
      <PushNotificationToast />
    </div>
  );
}
