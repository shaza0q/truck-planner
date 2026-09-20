/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
      colors: {
        app: {
          bg: '#F5F5F2',
          surface: '#FFFFFF',
          surfaceMuted: '#FAFAF8',
          text: '#202321',
          textSecondary: '#626862',
          textMuted: '#858A84',
          border: '#D9DAD5',
          borderSubtle: '#E7E7E2',
        },
        primary: {
          DEFAULT: '#245C4A',
          hover: '#1D4D3E',
          subtle: '#EEF4F1',
        },
        hos: {
          driving: '#245C4A',
          sleeper: '#60788A',
          onDuty: '#A66A21',
          offDuty: '#B8BCB7',
          fuel: '#D97706',
          break: '#B45309',
          error: '#B91C1C',
        }
      }
    },
  },
  plugins: [],
}

