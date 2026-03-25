/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // ConstructLex Pro design tokens — reference CSS variables
        bg:          'var(--cl-background)',
        surface:     'var(--cl-surface)',
        'surface-hover': 'var(--cl-surface-hover)',
        border:      'var(--cl-border)',
        'text-primary':   'var(--cl-text-primary)',
        'text-secondary': 'var(--cl-text-secondary)',
        accent:      'var(--cl-accent-primary)',
        'accent-2':  'var(--cl-accent-secondary)',
        // Score heatmap bands
        'heat-0': '#F0FAFA',
        'heat-1': '#A7D9D4',
        'heat-2': '#4DB8B0',
        'heat-3': '#0C9182',
        'heat-4': '#065F5B',
      },
      fontFamily: {
        display: ['Cormorant Garamond', 'Georgia', 'serif'],
        body:    ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}
