## Summary

Describe the purpose of the change and which user/developer workflow it affects.

## Changes

- 

## Verification

- [ ] `pnpm check`
- [ ] `pnpm test`
- [ ] `pnpm build`
- [ ] `pnpm contract:check`
- [ ] `pnpm nx e2e web --output-style=static` (or state why not run)
- [ ] Trusted-artifact compatibility checked if relevant and available (otherwise mark not applicable)

Provide actual commands and results rather than checking items that were not executed.

## Scientific and security impact

- [ ] No model retraining or unplanned change to fitted preprocessing, labels, metrics, or SHAP semantics
- [ ] No raw dataset, Joblib artifact, secret, or generated report committed
- [ ] Local-only security boundaries remain accurate, or changes are explicitly reviewed
- [ ] Documentation and generated API contract updated when needed

## Release and review notes

Base branch: `main` unless a release branch is explicitly needed.

Describe known risks, breaking changes, compatibility evidence and review requirements. Do **not** automatically publish a release or move an existing tag as part of an ordinary PR.
