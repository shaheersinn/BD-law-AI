# SKILL: Digital Atelier Design System Enforcement
## For ORACLE BD Intelligence Platform — frontend/ only

> Read this entire file before writing a single line of CSS, JSX, or Tailwind.
> Every agent touching the frontend must reference this. No exceptions.

---

## 1. What This Skill Covers

This skill governs all visual implementation work on `frontend/`. It translates the
"Digital Atelier / Editorial Brief" design spec (from `stitch_strategic_dashboard/
lexington_estate_ii/DESIGN.md`) into exact rules for the React + Tailwind + CSS
variables stack already in this repo.

---

## 2. The Existing System You Are REPLACING (Not Extending)

The current `design-system.css` uses a different design language:

| Current (OLD — remove these) | New (Digital Atelier — use these) |
|---|---|
| Cormorant Garamond | Newsreader |
| Plus Jakarta Sans | Manrope |
| `--bg: #F8F7F4` | `--color-surface: #f7f9fb` |
| `--text: #1A1A2E` | `--color-on-surface: #191c1e` |
| `--accent: #0C9182` | `--color-secondary: #306d58` |
| `--border: #E2E0DA` | Ghost border only — see Rule 1 |
| `--shadow-sm/md/lg` | `--shadow-ambient` only |

Do NOT add new variables alongside the old ones. Replace them. Any component still
referencing the old variable names after your changes is a bug.

---

## 3. The Five Non-Negotiable Rules

Read these before touching any file. Violations will break CI and the design review.

### Rule 1 — The No-Line Rule (MOST IMPORTANT)
`1px solid` borders for section dividers are **prohibited**. Full stop.

**Audit command — run this before committing:**
```bash
grep -rn "border-" frontend/src/ \
  | grep -v "rounded" \
  | grep -v "outline" \
  | grep -v "border-none" \
  | grep -v "border-0" \
  | grep -v "// " \
  | grep -v "\.md"
```

Zero results expected. If you see results, fix them using this substitution table:

| What you found | Replace with |
|---|---|
| `border border-gray-200` | Remove entirely. Use `bg-[var(--color-surface-container-low)]` on parent |
| `border-b` between list items | Remove. Add `py-4` spacing instead |
| `divide-y divide-gray-100` | Remove. Use alternating background or hover state |
| `border border-white` on modal/card | `outline outline-1 outline-[var(--color-outline-variant)]/15` |
| `border-solid` | Delete |

**The only permitted border:** Ghost border for containment ambiguity (white-on-white):
```css
outline: 1px solid rgba(197, 198, 206, 0.15);  /* outline-variant at 15% */
```
Use `outline`, never `border`, so it doesn't affect layout.

---

### Rule 2 — No Hardcoded Hex Values
Every colour in JSX and CSS must reference a CSS custom property or a Tailwind token
that maps to one. No `#04162e`, no `rgb(...)` inline.

**Correct:**
```jsx
<div className="bg-[var(--color-primary)] text-[var(--color-on-primary)]">
<div style={{ background: 'var(--color-surface-container-low)' }}>
```

**Wrong:**
```jsx
<div className="bg-[#04162e]">
<div style={{ background: '#f2f4f6' }}>
```

---

### Rule 3 — Surface Hierarchy (No Flat Pages)
Every page must use layered surfaces, not a single flat background.

Stack from bottom to top:
```
Page canvas:   --color-surface               (#f7f9fb)
  └─ Sections: --color-surface-container-low (#f2f4f6)  ← sidebar, panels
       └─ Cards/inputs: --color-surface-container-lowest (#ffffff) ← interactive
            └─ Hover state: --color-surface-container-high (#e8eaed)
```

Floating elements (modals, dropdowns, nav on scroll):
```css
background: rgba(255, 255, 255, 0.8);
backdrop-filter: blur(20px);
```

---

### Rule 4 — Typography Must Use Exact Classes
Never invent font sizes. Use only these utility classes (defined in `design-system.css`):

| Class | Font | Size | Weight | Tracking |
|---|---|---|---|---|
| `.type-display-lg` | Newsreader | 3.5rem | 400 | -0.02em |
| `.type-headline-sm` | Newsreader | 1.5rem | 500 | -0.01em |
| `.type-title-sm` | Manrope | 1.0rem | 600 | +0.01em |
| `.type-body-md` | Manrope | 0.875rem | 400 | +0.01em, line-height 1.6 |
| `.type-label-sm` | Manrope | 0.6875rem | 700 | +0.05em, UPPERCASE |

Use `.type-display-lg` and `.type-headline-sm` ONLY for editorial moments:
product name, page title, empty state headline. Never for data labels.

Use `.type-label-sm` for: section headers, column headers, chip labels, metadata tags.

---

### Rule 5 — No Black
Never use `#000000` or Tailwind's `text-black`/`bg-black`.

| Instead of | Use |
|---|---|
| `text-black` | `text-[var(--color-on-surface)]` |
| `bg-black` | `bg-[var(--color-primary)]` |
| `border-black` | Illegal under Rule 1 |

---

## 4. Full Token Reference

Add all of these to `:root` in `frontend/src/styles/design-system.css`,
replacing the existing token set:

```css
:root {
  /* ── Core palette ─────────────────────────────────── */
  --color-primary:                   #04162e;
  --color-primary-container:         #1a2b44;
  --color-on-primary:                #ffffff;

  --color-secondary:                 #306d58;
  --color-secondary-container:       #adedd3;
  --color-on-secondary-container:    #306d58;

  --color-surface:                   #f7f9fb;
  --color-surface-container-lowest:  #ffffff;
  --color-surface-container-low:     #f2f4f6;
  --color-surface-container-high:    #e8eaed;

  --color-on-surface:                #191c1e;
  --color-on-surface-variant:        #44474e;

  --color-outline-variant:           #c5c6ce;

  /* ── Score heatmap (keep from existing system) ────── */
  --score-0: #F0FAFA;
  --score-1: #A7D9D4;
  --score-2: #4DB8B0;
  --score-3: #0C9182;
  --score-4: #065F5B;

  /* ── Semantic states ──────────────────────────────── */
  --color-error:      #dc2626;
  --color-error-bg:   #fef2f2;
  --color-warning:    #d97706;
  --color-warning-bg: #fffbeb;
  --color-success:    #059669;
  --color-success-bg: #f0fdf4;

  /* ── Typography ───────────────────────────────────── */
  --font-editorial:   'Newsreader', Georgia, serif;
  --font-data:        'Manrope', system-ui, sans-serif;
  --font-mono:        'JetBrains Mono', 'Courier New', monospace;

  /* ── Layout ───────────────────────────────────────── */
  --sidebar-width:      240px;
  --sidebar-collapsed:  64px;

  /* ── Elevation ────────────────────────────────────── */
  --shadow-ambient: 0 0 40px -10px rgba(25, 28, 30, 0.06);

  /* ── Radius ───────────────────────────────────────── */
  --radius-md:   0.375rem;   /* 6px  — buttons, inputs */
  --radius-xl:   0.75rem;    /* 12px — cards */
  --radius-full: 9999px;     /* chips */

  /* ── Transitions ──────────────────────────────────── */
  --transition-fast:   150ms ease-out;
  --transition-card:   200ms ease-out;
}
```

---

## 5. Google Fonts — Exact Import

In `frontend/index.html`, replace the existing `<link>` tags with:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,500;1,400&family=Manrope:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

Then update `design-system.css` `@import` to match, or remove the CSS `@import`
entirely if `index.html` already handles it (avoid double-loading).

---

## 6. Tailwind Config — Exact Replacement

Replace the contents of `frontend/tailwind.config.js` with:

```js
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
        // Score heatmap
        'heat-0': '#F0FAFA',
        'heat-1': '#A7D9D4',
        'heat-2': '#4DB8B0',
        'heat-3': '#0C9182',
        'heat-4': '#065F5B',
      },
      fontFamily: {
        editorial: ['Newsreader', 'Georgia', 'serif'],
        data:      ['Manrope', 'system-ui', 'sans-serif'],
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
```

---

## 7. Component Patterns — Copy-Paste Templates

### Primary Button
```jsx
<button className="
  px-5 py-2.5 rounded-md font-data font-semibold text-sm tracking-wide
  text-[var(--color-on-primary)]
  bg-gradient-to-b from-[var(--color-primary)] to-[var(--color-primary-container)]
  hover:opacity-90 transition-opacity duration-150
">
  Action Label
</button>
```

### Secondary Button (Emerald)
```jsx
<button className="
  px-5 py-2.5 rounded-md font-data font-semibold text-sm
  bg-[var(--color-secondary-container)]
  text-[var(--color-on-secondary-container)]
  hover:opacity-85 transition-opacity duration-150
">
  Secondary Action
</button>
```

### Card
```jsx
<div className="
  rounded-xl p-6
  bg-[var(--color-surface-container-lowest)]
  shadow-ambient
  hover:shadow-card hover:-translate-y-0.5
  transition-all duration-200 ease-out
">
  {children}
</div>
```

### Data Chip (Signal Type / Practice Area)
```jsx
<span className="
  inline-flex items-center px-2.5 py-1 rounded-full
  bg-[var(--color-surface-container-high)]
  font-data text-[11px] font-semibold tracking-wider uppercase
  text-[var(--color-on-surface-variant)]
">
  {label}
</span>
```

### Section Header (Sidebar / Column)
```jsx
<h3 className="
  font-data text-[11px] font-bold tracking-[0.05em] uppercase
  text-[var(--color-on-surface-variant)] mb-3
">
  {title}
</h3>
```

### Editorial Page Title
```jsx
<h1 className="type-display-lg font-editorial text-[var(--color-primary)]">
  ORACLE
</h1>
```

### Glass Navbar
```jsx
<nav className="
  sticky top-0 z-50 px-8 py-4
  bg-white/80 backdrop-blur-[20px]
  border-b-0  {/* No borders — Rule 1 */}
">
```

### Input Field
```jsx
<input className="
  w-full px-3 py-2 rounded-md font-data text-sm
  bg-[var(--color-surface-container-lowest)]
  text-[var(--color-on-surface)]
  outline outline-1 outline-[var(--color-outline-variant)]/15
  focus:outline-[var(--color-outline-variant)]/40
  focus:ring-0 transition-all duration-150
  placeholder:text-[var(--color-on-surface-variant)]
" />
```

### Sidebar Nav Item
```jsx
// Active state via background shift, never a border or indicator dot
<li className={`
  flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer
  font-data text-sm transition-colors duration-150
  ${active
    ? 'bg-[var(--color-surface-container-high)] text-[var(--color-on-surface)] font-semibold'
    : 'text-[var(--color-on-surface-variant)] hover:bg-[var(--color-surface-container-high)]'
  }
`}>
```

---

## 8. Layout Rules

### Asymmetric Grid (Use This — Not 50/50)
```jsx
<div className="grid grid-cols-3 gap-8">
  <div className="col-span-2">{/* Main content */}</div>
  <div className="col-span-1">{/* Secondary panel */}</div>
</div>
```

### Section Spacing
Between major page sections: `mb-14` (3.5rem = spacing-14). Never less.
Between cards within a section: `gap-5` or `gap-6`.
Between list items: `py-4` vertical padding. No dividers.

---

## 9. ORACLE-Specific Data Patterns

These patterns are specific to this app's backend output and must be consistent
across all pages that render scoring data.

### Practice Area Display
The backend returns 34 practice areas. Always render them as `.type-label-sm` chips.
Never as a bare list or dropdown. Group them by category if space is limited.

### Score Horizon Toggle (30 / 60 / 90 day)
```jsx
// Query param: GET /api/v1/scores?horizon=30
const [horizon, setHorizon] = useState(30);
// Render as three secondary buttons, active one uses primary gradient
```

### Confidence Interval
The ML model returns `confidence_low`, `confidence_high`, `score`. Always render
the interval as a subtle bar behind the score number, not just the point estimate.
Use `--color-secondary-container` for the interval band, `--color-secondary` for
the point estimate marker.

---

## 10. Pre-Commit Checklist

Run ALL of these before `git add`:

```bash
# 1. No 1px borders
grep -rn "border-" frontend/src/ | grep -Ev "rounded|outline|border-none|border-0|//|\.md|node_modules"

# 2. No hardcoded hex values in JSX/JS files
grep -rn "#[0-9A-Fa-f]\{3,6\}" frontend/src/ | grep -Ev "design-system\.css|tailwind\.config|\.md|score-|heat-"

# 3. Build passes
cd frontend && npm run build

# 4. Lint passes
cd frontend && npm run lint

# 5. Old font references removed
grep -rn "Cormorant\|Plus Jakarta\|cormorant\|jakarta" frontend/src/
# Expected: zero results
```

Zero violations on all five checks before committing.
