/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary:                   'var(--color-primary)',
        'primary-container':       'var(--color-primary-container)',
        'on-primary':              'var(--color-on-primary)',
        secondary:                 'var(--color-secondary)',
        'secondary-container':     'var(--color-secondary-container)',
        'on-secondary-container':  'var(--color-on-secondary-container)',
        surface:                   'var(--color-surface)',
        'surface-lowest':          'var(--color-surface-container-lowest)',
        'surface-low':             'var(--color-surface-container-low)',
        'surface-high':            'var(--color-surface-container-high)',
        'on-surface':              'var(--color-on-surface)',
        'on-surface-variant':      'var(--color-on-surface-variant)',
        'outline-variant':         'var(--color-outline-variant)',
        // Score heatmap bands
        'heat-0': '#F0FAFA',
        'heat-1': '#A7D9D4',
        'heat-2': '#4DB8B0',
        'heat-3': '#0C9182',
        'heat-4': '#065F5B',
      },
      fontFamily: {
        editorial: ['DM Serif Display', 'Georgia', 'serif'],
        data:      ['DM Sans', 'system-ui', 'sans-serif'],
        mono:      ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      boxShadow: {
        ambient: '0 0 40px -10px rgba(25, 28, 30, 0.06)',
        card:    '0 0 40px -10px rgba(25, 28, 30, 0.06)',
      },
      borderRadius: {
        md:   '0.375rem',
        xl:   '0.75rem',
        full: '9999px',
      },
    },
  },
  plugins: [],
}
