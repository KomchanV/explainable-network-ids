---
name: Explainable Network IDS
description: Evidence-first offline network-flow analysis workspace
colors:
  "background": "#f4f6f6"
  "foreground": "#1c2b30"
  "card": "#ffffff"
  "card-foreground": "#1c2b30"
  "popover": "#ffffff"
  "popover-foreground": "#1c2b30"
  "primary": "#116b60"
  "primary-foreground": "#ffffff"
  "secondary": "#e9efee"
  "secondary-foreground": "#263d3b"
  "muted": "#e9efee"
  "muted-foreground": "#526466"
  "accent": "#dfefeb"
  "accent-foreground": "#125d53"
  "destructive": "#b42332"
  "border": "#cbd6d5"
  "input": "#788b8a"
  "ring": "#147d70"
  "benign": "#0f766e"
  "benign-surface": "#e0f4ef"
  "danger": "#b42332"
  "danger-surface": "#fcebed"
  "rail": "#172b2a"
  "rail-text": "#dce9e5"
  "rail-muted": "#a6bdb5"
  "rail-active": "#29453e"
  "rail-accent": "#8ad7bd"
  "dark-background": "#101819"
  "dark-foreground": "#e5edeb"
  "dark-card": "#172224"
  "dark-card-foreground": "#e5edeb"
  "dark-popover": "#172224"
  "dark-popover-foreground": "#e5edeb"
  "dark-primary": "#77d6bf"
  "dark-primary-foreground": "#102b26"
  "dark-secondary": "#243233"
  "dark-secondary-foreground": "#e5edeb"
  "dark-muted": "#243233"
  "dark-muted-foreground": "#a6b8b5"
  "dark-accent": "#253e38"
  "dark-accent-foreground": "#a4e4d4"
  "dark-destructive": "#fda4af"
  "dark-border": "#364847"
  "dark-input": "#748d87"
  "dark-ring": "#77d6bf"
  "dark-benign": "#5eead4"
  "dark-benign-surface": "#183b34"
  "dark-danger": "#fda4af"
  "dark-danger-surface": "#422b31"
typography:
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.75rem"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-.025em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: ".875rem"
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: ".75rem"
    fontWeight: 500
  measurement:
    fontFamily: "'JetBrains Mono Variable', monospace"
    fontSize: "1.5rem"
    lineHeight: 1.3333333333333333
rounded:
  "sm": ".375rem"
  "md": ".5rem"
  "lg": ".75rem"
  "xl": "1rem"
spacing:
  "unit": ".25rem"
  "2": ".5rem"
  "3": ".75rem"
  "4": "1rem"
  "5": "1.25rem"
  "6": "1.5rem"
  "8": "2rem"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.md}"
    padding: ".5rem 1rem"
  button-secondary:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: ".5rem 1rem"
  button-destructive:
    backgroundColor: "{colors.card}"
    textColor: "{colors.danger}"
    rounded: "{rounded.md}"
    padding: ".5rem 1rem"
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: ".5rem .75rem"
  badge-benign:
    backgroundColor: "{colors.benign-surface}"
    textColor: "{colors.benign}"
    rounded: "{rounded.sm}"
    padding: ".25rem .5rem"
  badge-danger:
    backgroundColor: "{colors.danger-surface}"
    textColor: "{colors.danger}"
    rounded: "{rounded.sm}"
    padding: ".25rem .5rem"
  panel:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.xl}"
    padding: "1.25rem"
  navigation-active:
    backgroundColor: "{colors.rail-active}"
    textColor: "{colors.rail-text}"
    rounded: "{rounded.md}"
    padding: ".8rem .9rem"
---

# Design System: Explainable Network IDS

## Overview

**Creative North Star: "Technical field guide"**

A restrained technical field guide for investigating saved network flows. Graphite navigation, mineral teal actions and cool neutral work surfaces keep predictions, measurements and explanations legible. This is an operational interface: system sans supports reading and wayfinding; monospace supports measurements and identifiers.

The workspace presents model output with nearby scientific context. Uploaded prediction distribution, local class-1 SHAP and saved held-out evaluation remain visibly distinct.

**Key Characteristics:**
- Graphite navigation and mineral teal actions
- Compact headings, readable controls and aligned measurements
- Border-defined surfaces with semantic scientific color
- Responsive investigation drawer and explicit data caveats

## Colors

### Primary
Mineral teal identifies primary actions, links and focus. The light and dark action pairs are separately defined in the frontmatter; dark mode uses brighter teal with dark action text.

### Secondary
Scientific class and contribution colors use BENIGN teal and DDoS red, with their own tinted badge surfaces. Destructive controls use the danger role rather than treating every red mark as an action.

### Neutral
Cool background, card and muted tones separate reading surfaces. Foreground, muted foreground, border and input roles supply text and boundaries. The graphite rail keeps its own text, muted, active and accent colors in both themes. `dark-` frontmatter keys record `.dark` overrides; unprefixed rail values continue in dark mode. CSS custom properties in `apps/web/src/routes/layout.css` remain the implementation authority.

**The Semantic Direction Rule.** Red marks predicted DDoS or increasing P(DDoS); teal marks predicted BENIGN or decreasing P(DDoS). Pair color with readable class names or signed direction. Neither color establishes a verified incident.

## Typography

**Body and heading font:** system sans, using the frontmatter stack. **Measurement font:** JetBrains Mono Variable with monospace fallback. The waterfall's numeric column uses generic monospace.

### Hierarchy
- **Headline:** compact page title, not decorative display lettering.
- **Title:** section headings; smaller investigation headings also use an observed 1.125rem semibold step.
- **Body:** operational prose and table content. Page introductions use a more open 1.5rem line-height; direct main paragraphs cap at 75ch.
- **Label:** metadata, field labels and chart annotations. Badges use weight 600.
- **Measurement:** summary metrics; compact counts use 1rem and table measurements use the body size. Tables use tabular numerals.

**The Operational Type Rule.** Use sans for headings, labels and explanatory prose; reserve monospace for numeric output and technical identifiers.

## Layout

The desktop workspace is a 236px sticky navigation rail plus `minmax(0, 1fr)` content. The utility header is at least 68px tall; main content has a 1600px maximum width and 2rem padding. At 900px and below navigation becomes a disclosure, the header minimum becomes 64px, and main padding becomes 1.5rem vertically and 1.25rem horizontally.

Use the observed quarter-rem spacing rhythm, with panels padded 1.25rem and 1.5rem from the 640px small-screen utility breakpoint. The filter layout collapses its two groups at 1200px and reduces fields to two columns at 600px. Summary metrics and summary strips adapt at 700px. First-use content reduces padding at 1100px and stacks at 700px. Model-insight utility grids expand at 640px and 1024px.

Wide tables scroll within focusable regions; identifiers wrap where needed. Compact dataset counts and disclosure sections avoid making investigation wait behind repeated cards.

## Elevation & Depth

Ordinary workspace panels are flat, separated with borders and tonal surfaces. The right investigation drawer uses `-12px 0 36px #0003` for structural separation, not a universal card shadow.

**The Flat Workspace Rule.** Separate ordinary surfaces with tone and borders. The investigation drawer carries the structural shadow.

## Shapes

Controls use the medium radius, badges the small radius, table containers and many sections the medium radius, distribution/filter surfaces the large radius, and shared panels the extra-large radius. Borders are thin rules. Charts use straight tracks, bars and endpoint marks rather than decorative illustration.

## Components

### Buttons
Workspace controls have a 2.75rem minimum height, body-sized medium text, a thin border and medium corners. Primary controls use the action pair and a 90% primary hover fill; secondary controls use card surfaces and accent hover. Destructive confirmation uses danger text/border and danger-surface hover. Active buttons move down 1px. Disabled controls reduce opacity to 50%. The separate library Button retains square, smaller variants; it is not the workspace sizing baseline.

### Inputs / Fields
Native labeled inputs and selects use background surfaces, input borders, medium corners and 2.75rem minimum height. Labels use muted small type with .5rem separation. Global keyboard focus is a 2px ring with 3px offset; workspace buttons override the offset to 2px. Errors use readable alert text, associations and bordered containers.

### Chips
Prediction badges are noninteractive class labels, with semantic foreground/surface pairs, small corners and semibold label text. They are not severity scores.

### Cards / Containers
Shared panels use card surfaces, border rules, extra-large corners and responsive padding. Summary strips and evaluation metrics also use open border-separated layouts; not every section is a card.

### Navigation
Rail links combine library icons with readable labels. Active and hover links use rail-active fill and rail-text; the active link adds semibold weight and `aria-current`. Below the navigation breakpoint, an explicitly labeled disclosure button controls visibility. Theme selection offers System, Light and Dark.

### Flow investigation drawer
A native nonmodal desktop dialog keeps comparison with flow rows available. At 640px and below it becomes a full-width native modal. Desktop width is `min(720px, 92vw)`; height is 100dvh. The sticky header and scrolling content retain access to Close. Close and Escape restore the origin focus; breakpoint changes preserve the origin while reopening in the appropriate native mode. Prediction and class-1 explanation stay adjacent.

### Scientific figures and states
Distribution bars retain readable class counts. SHAP uses red for increasing and teal for decreasing class-1 P(DDoS), with direction text and signed values; chart domains retain additive paths outside zero to one. Global SHAP identifies its uploaded-data sample, and saved evaluation identifies separate labeled test data. Loading names the operation; unavailable values are not zero. Reduced-motion preference disables animations, transitions and smooth scrolling.

## Do's and Don'ts

### Do:
- **Do** keep probability and SHAP caveats beside their output.
- **Do** preserve labels, visible focus, textual status and keyboard-accessible horizontal scrolling.
- **Do** use the semantic light/dark variables rather than hard-coded light surfaces.
- **Do** preserve native drawer modes and return focus to the originating record.

### Don't:
- **Don't** describe uncalibrated P(DDoS) as confidence, severity or verified ground truth.
- **Don't** equate uploaded predicted DDoS share with held-out evaluation accuracy.
- **Don't** introduce cyberpunk effects or fabricated live monitoring claims.
