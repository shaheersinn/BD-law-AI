# Design System Specification: The Digital Atelier

## 1. Overview & Creative North Star

**Creative North Star: "The Editorial Brief"**
This design system moves away from the sterile emptiness of extreme minimalism toward a "SaaS-plus" aesthetic—a high-density, high-value environment tailored for the modern legal professional. It is inspired by the meticulous layout of a premium broadsheet and the precision of a bespoke timepiece. 

By leveraging "miniature" typography—smaller scales with generous leading—we create a sense of intellectual density without clutter. We break the "template" look by favoring **intentional asymmetry** and **tonal depth** over rigid grids and harsh borders. The interface should feel like a series of curated layers, where information isn't just displayed, it is presented.

---

## 2. Colors & Surface Philosophy

The palette is anchored in professional authority. We utilize a "Slate-to-Ivory" spectrum for surfaces, punctuated by a deep, commanding Navy and an Emerald accent that signals growth and precision.

### The "No-Line" Rule
**Explicit Instruction:** 1px solid borders are prohibited for sectioning. Boundaries must be defined solely through background color shifts or tonal transitions. Use `surface-container-low` for page sections and `surface-container-lowest` (pure white) for interactive elements.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of fine paper.
- **Base Layer:** `surface` (#f7f9fb) – The canvas.
- **Section Layer:** `surface-container-low` (#f2f4f6) – For sidebar backgrounds or large content areas.
- **Primary Interaction Layer:** `surface-container-lowest` (#ffffff) – For cards and input fields.
- **The Glass & Gradient Rule:** For floating headers or navigation, use `surface-container-lowest` at 80% opacity with a `backdrop-blur` of 20px. 

### Signature Textures
Main CTAs should use a subtle vertical gradient: 
`from: primary (#04162e) to: primary-container (#1a2b44)`. This adds a "weighted" feel to the button, suggesting durability and importance.

---

## 3. Typography: The Miniature Scale

We utilize a dual-font strategy: **Newsreader** (Serif) for authoritative editorial moments and **Manrope** (Sans-serif) for high-performance data density.

| Role | Font | Size | Weight | Tracking |
| :--- | :--- | :--- | :--- | :--- |
| **Display-LG** | Newsreader | 3.5rem | 400 | -0.02em |
| **Headline-SM** | Newsreader | 1.5rem | 500 | -0.01em |
| **Title-SM** | Manrope | 1.0rem | 600 | 0.01em |
| **Body-MD** | Manrope | 0.875rem (14px) | 400 | 0.01em |
| **Label-SM** | Manrope | 0.6875rem (11px) | 700 | 0.05em (Caps) |

**Editorial Hierarchy:** Use `Headline` styles for storytelling and `Label-SM` in all-caps for metadata. The small body scale (14px) allows for high data density, but must be paired with a line-height of `1.6` to ensure premium legibility.

---

## 4. Elevation & Depth

### The Layering Principle
Depth is achieved by stacking tones. Place a `surface-container-lowest` card on a `surface-container-low` section. This "natural lift" replaces the need for high-contrast shadows.

### Ambient Shadows
When an element must float (e.g., a dropdown or modal), use the following shadow specification:
- **Blur:** 40px
- **Spread:** -10px
- **Opacity:** 6%
- **Color:** Derived from `on-surface` (#191c1e) to create a soft, atmospheric glow rather than a muddy smudge.

### The "Ghost Border" Fallback
In rare cases where containment is visually ambiguous (e.g., pure white on pure white), use a **Ghost Border**: `outline-variant` (#c5c6ce) at **15% opacity**. Never use 100% opaque borders.

---

## 5. Components

### Cards & Lists
*   **Containment:** Use `rounded-xl` (0.75rem) for cards. No dividers.
*   **Separation:** Distinguish list items using vertical white space (`spacing-4`) or a hover state that shifts the background to `surface-container-high`.
*   **Micro-interaction:** On hover, a card should subtly lift with a `0.2s ease-out` transition and a slight expansion of the ambient shadow.

### Buttons
*   **Primary:** Gradient of `primary` to `primary-container`. `rounded-md`. Type: `label-md` in `on-primary`.
*   **Secondary (The Emerald Accent):** Use `secondary-container` (#adedd3) with `on-secondary-container` (#306d58) text. This provides a "soft-action" feel.
*   **Tertiary:** Text-only using `primary` with a 2px underline appearing only on hover.

### Inputs & Fields
*   **Canvas:** `surface-container-lowest` background. 
*   **States:** On focus, the ghost border increases opacity to 40% and the label (Manrope 11px) shifts to the `secondary` (emerald) color.

### Data Chips
*   Compact, `rounded-full`, using `surface-container-high` backgrounds. Use Manrope 11px Semi-bold for the label.

---

## 6. Do's and Don'ts

### Do:
*   **Do** embrace white space. "Miniature" type requires "Maximalist" margins. Use `spacing-16` (3.5rem) between major sections.
*   **Do** use asymmetrical layouts. A 2/3 and 1/3 column split is more "editorial" than a symmetrical 50/50.
*   **Do** use high-quality, thin-stroke (1.5px) icons in `primary-container` to add "perceived value."

### Don't:
*   **Don't** use black (#000000). Use `on-surface` (#191c1e) for text and `primary` (#04162e) for depth.
*   **Don't** use 1px solid dividers to separate list items. Use the `surface-container` tiers to create logical groups.
*   **Don't** over-round elements. Keep to the `rounded-md` (0.375rem) or `rounded-xl` (0.75rem) scales to maintain a professional, architectural feel.

### Accessibility Note:
While we utilize a "miniature" type scale, we maintain contrast ratios of at least 7:1 for all body text by using `on-surface` against `surface` or `white` backgrounds.