/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Required exact palette for MailMind AI clean SaaS redesign
        sidebar: {
          DEFAULT: '#17243B',
          hover:   '#1F314F',
          active:  '#253A5E',
          border:  '#223554',
          text:    '#E2E8F0',
          muted:   '#94A3B8',
        },
        surface: {
          light:   '#F5F7FC',
          card:    '#FFFFFF',
          border:  '#E5EAF2',
          text:    '#1E293B',
          muted:   '#7B8497',
        },
        primary: {
          blue:    '#4169E1',
          hover:   '#3457C8',
          light:   '#E8EEFF',
        },
        // Dark mode equivalents
        dark: {
          bg:      '#0F172A',
          card:    '#1E293B',
          border:  '#334155',
          text:    '#F8FAFC',
          muted:   '#94A3B8',
        },
        // Legacy compatibility
        navy: {
          950: '#050918',
          900: '#080d1f',
          800: '#0d1530',
          700: '#111d3d',
          600: '#162349',
        },
        brand: {
          blue:   '#4169E1',
          indigo: '#6366f1',
          violet: '#7c3aed',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(0, 0, 0, 0.04)',
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
        'dropdown': '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05)',
      },
      borderRadius: {
        'card': '0.75rem', // 12px
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'slide-down': 'slideDown 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
