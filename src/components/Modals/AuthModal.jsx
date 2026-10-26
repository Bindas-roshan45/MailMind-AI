import { useState } from 'react';
import { Mail, Lock, User, Sparkles, AlertCircle, ArrowRight, Eye, EyeOff } from 'lucide-react';
import api from '../../services/api';
import toast from 'react-hot-toast';

export default function AuthModal({ isOpen, onClose, onSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isSignUp) {
        if (!name.trim()) {
          throw new Error('Please enter your full name');
        }
        if (password.length < 8) {
          throw new Error('Password must be at least 8 characters long');
        }
        const res = await api.auth.register({
          name: name.trim(),
          email: email.trim().toLowerCase(),
          password,
        });
        if (res?.access_token) {
          localStorage.setItem('mailmind_token', res.access_token);
          toast.success(`Welcome to MailMind AI, ${res.user?.name || name}!`);
          onSuccess?.(res.access_token);
          onClose?.();
        }
      } else {
        const res = await api.auth.login({
          email: email.trim().toLowerCase(),
          password,
        });
        if (res?.access_token) {
          localStorage.setItem('mailmind_token', res.access_token);
          toast.success(`Welcome back, ${res.user?.name || 'User'}!`);
          onSuccess?.(res.access_token);
          onClose?.();
        }
      }
    } catch (err) {
      const msg = err?.data?.detail || err?.message || 'Authentication failed. Please check your credentials.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleOAuth = async () => {
    setError(null);
    setOauthLoading(true);
    try {
      const res = await api.auth.getGoogleAuthUrl();
      if (res?.success && res.data?.auth_url) {
        window.location.href = res.data.auth_url;
      } else {
        setError(res?.data?.setup_instructions || 'Google OAuth is not configured on this environment.');
      }
    } catch (err) {
      setError(err?.data?.detail || err?.message || 'Failed to initiate Google authentication.');
    } finally {
      setOauthLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-white dark:bg-[#1E293B] rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700/80 overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-slate-100 dark:border-slate-800 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-tr from-[#4169E1] to-indigo-500 text-white shadow-md shadow-indigo-500/20 mb-3">
            <Sparkles className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            {isSignUp ? 'Create your MailMind Account' : 'Sign in to MailMind AI'}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {isSignUp
              ? 'Start supercharging your inbox with production AI'
              : 'Enter your credentials or connect with Google'}
          </p>
        </div>

        {/* Tab switch */}
        <div className="flex border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 p-1">
          <button
            type="button"
            onClick={() => { setIsSignUp(false); setError(null); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              !isSignUp
                ? 'bg-white dark:bg-[#1E293B] text-[#4169E1] shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsSignUp(true); setError(null); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              isSignUp
                ? 'bg-white dark:bg-[#1E293B] text-[#4169E1] shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 text-rose-700 dark:text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {isSignUp && (
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  required
                  placeholder="Roshan Kumar"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4169E1]/30 focus:border-[#4169E1]"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="email"
                required
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4169E1]/30 focus:border-[#4169E1]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Password {isSignUp && <span className="text-[11px] text-slate-400 font-normal">(min 8 characters)</span>}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={isSignUp ? 8 : 1}
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-10 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#4169E1]/30 focus:border-[#4169E1]"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-[#4169E1] hover:bg-blue-600 text-white font-medium text-sm transition-colors shadow-sm disabled:opacity-50 cursor-pointer"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <span>{isSignUp ? 'Create Account' : 'Sign In'}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          <div className="relative py-2 flex items-center justify-center">
            <div className="border-t border-slate-200 dark:border-slate-700 w-full" />
            <span className="bg-white dark:bg-[#1E293B] px-3 text-[11px] text-slate-400 uppercase tracking-wider absolute">
              or
            </span>
          </div>

          <button
            type="button"
            onClick={handleGoogleOAuth}
            disabled={oauthLoading}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-medium transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.04h3.88c2.28-2.09 3.665-5.18 3.665-9.14z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.04c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.13C3.27 21.43 7.33 24 12 24z"
              />
              <path
                fill="#FBBC05"
                d="M5.28 14.28c-.25-.72-.38-1.49-.38-2.28s.13-1.56.38-2.28V6.59H1.25C.45 8.18 0 10.03 0 12s.45 3.82 1.25 5.41l4.03-3.13z"
              />
              <path
                fill="#EA4335"
                d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.27 2.57 1.25 6.59l4.03 3.13c.95-2.83 3.6-4.97 6.72-4.97z"
              />
            </svg>
            <span>{oauthLoading ? 'Redirecting to Google...' : 'Continue with Google OAuth'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
