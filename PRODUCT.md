# Explainable Network IDS
<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
Security analysts, network administrators, researchers, and students investigating saved network flow datasets (user brief).

## Product Purpose
Classify offline CIC-IDS2017 CSV flows as BENIGN or DDoS and examine the model inputs and SHAP explanations behind predictions.

## Operating Context
Nx monorepo, SvelteKit/Svelte 5 frontend, FastAPI adapter, existing Python Random Forest and SHAP engine. Local offline batch analysis, not a live SOC service.

## Capabilities and Constraints
Import and validate CSV; batch inference; temporary current analysis; filter, sort, paginate and inspect flows; export predictions; delete analysis; local and deterministic sampled global SHAP; saved held-out evaluation. No alert management, live capture, permanent history, incident verification, or settings API. Browser storage remembers one analysis ID and theme preference. Preserve backend and generated API contracts.

## Evidence on Hand
Actual API outputs and saved model provenance. E2E synthetic model is test evidence only. P(DDoS) is uncalibrated probability, never confidence or severity; SHAP explains class-1 P(DDoS), including BENIGN predictions. Evaluation accuracy is independent of uploaded prediction share.

## Brand Commitments
Explainable Network IDS. Professional, restrained, technical and approachable. No cyberpunk effects or fabricated operational claims.

## Product Principles
- Make import → prediction → investigation → explanation clear.
- Keep scientific caveats beside relevant data.
- Distinguish unavailable results from zero and model output from verified facts.
- Preserve working integrations and use actual data.

## Accessibility & Inclusion
Target WCAG 2.2 AA; keyboard operation, labeled controls, visible focus, semantic status text, reduced motion and mobile layouts.
