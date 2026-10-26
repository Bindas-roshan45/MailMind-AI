import { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { AppProvider, useApp } from './context/AppContext';
import Dashboard from './components/Dashboard/Dashboard';
import AuthModal from './components/Modals/AuthModal';

function AppInner() {
  const { theme, authModalOpen, setAuthModalOpen, refreshInitialData } = useApp();

  useEffect(() => {
    document.documentElement.classList.toggle('dark',  theme === 'dark');
    document.documentElement.classList.toggle('light', theme === 'light');
  }, [theme]);

  return (
    <>
      <Dashboard />
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={() => {
          setAuthModalOpen(false);
          refreshInitialData();
        }}
      />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: theme === 'dark' ? '#1E293B' : '#FFFFFF',
            color: theme === 'dark' ? '#F8FAFC' : '#1E293B',
            border: theme === 'dark' ? '1px solid #334155' : '1px solid #E5EAF2',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            fontSize: '13px',
            borderRadius: '10px',
            fontWeight: 500,
          },
        }}
      />
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  );
}
