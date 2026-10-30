# Explainable IDS design system

The security analytics workspace is an Operate surface: legible data, predictable controls and honest scientific context take priority. Its four areas are Overview, Analyses, Traffic Explorer and Model Insights. No permanent history or live monitoring is implied.

## Foundations

`apps/web/src/routes/layout.css` is the authoritative token source. Tailwind and the existing shadcn Button consume the same semantic variables. No new UI dependency is required.

| Role | Light | Dark |
| --- | --- | --- |
| Background | #F3F6FA | #0B1220 |
| Surface | #FFFFFF | #172235 |
| Text | #172235 | #E8EEF7 |
| Secondary text | #526078 | #A6B5CC |
| Action | #1D4ED8 | #93B8FF |
| BENIGN / decreasing contribution | #0F766E | #5EEAD4 |
| DDoS / increasing contribution | #B42332 | #FDA4AF |
| Border | #CBD5E1 | #35465F |
| Input boundary | #7889A0 | #7185A2 |

Action shades prioritize text contrast in both themes. The OS color preference is the default. A System/Light/Dark selector persists only the preference in browser storage. An early head script applies the theme before paint; the layout tracks OS changes. Storage failures do not prevent theme changes or analysis.

Use system sans for interface text and JetBrains Mono for numeric output, identifiers and feature names. Page headings are 30px, section headings 18–20px, body 14px and metadata 12px; avoid uppercase decorative headings. Use a 4px spacing base, 20–24px panel padding, 32px page padding (20px mobile). Panels use a 12px radius and a subtle border. Inputs/buttons have a 44px minimum height, 6–8px radius and visible 2px focus outlines.

## Shared patterns

- `console-button` / existing Button: consistent action shape, disabled feedback, hover and keyboard focus. Blue identifies primary actions.
- `control-label`: explicit labels and native inputs/selects, with theme-aware surfaces and text.
- `panel`, `error-box`, `badge`: consistent surface, actionable error and semantic prediction states. Color always accompanies readable text.
- `AnalysisSummary`: real counts and distribution, filename, progressively disclosed provenance and timestamps. Predicted DDoS share is never accuracy.
- `FlowDrawer`: native nonmodal desktop dialog; full-width modal at <=640px for keyboard containment. Close/Escape returns focus to its originating record. Breakpoint changes preserve the origin and reopen with the appropriate native mode. Inner content scrolls independently.
- Loading states name the operation. Upload/SHAP use indeterminate text because the API exposes no incremental progress. Empty states explain the next action. API errors retain server messages and relevant retry/import actions.

The sidebar becomes a disclosure menu below 900px. Main content uses `minmax(0, 1fr)` to contain wide tables. Long identifiers wrap; full contribution tables scroll horizontally with keyboard access. Reduced-motion preferences disable nonessential animation.

## Scientific presentation

SHAP always explains class-1 P(DDoS), even for BENIGN predictions. Positive/negative contributions show direction relative to the model baseline; the full table preserves model order and actual transformed values. Grouped waterfall terms retain the full additive sum. Global SHAP describes a deterministic uploaded-data sample, not the training population. Saved evaluation and uploaded-data explanations are separate sections. Never call uncalibrated probability confidence, threat severity or causal attack evidence.
