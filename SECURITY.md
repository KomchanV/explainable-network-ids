# Security policy and scope

## Supported use

The current development line is `v0.2.0-alpha.1`, an **offline, local-only academic prototype** for BENIGN/DDoS network-flow classification. It is **not** a production intrusion-detection system.

Only locally trusted, operator-controlled Joblib model files are accepted. Joblib/Pickle deserialization may execute code; never load artifacts from untrusted sources. No browser endpoint accepts model uploads.

## Known security boundaries

- The API has no authentication or authorization and must stay bound to loopback.
- CORS origin restrictions do **not** provide access control; temporary analysis IDs must not be treated as user isolation.
- CSV analysis is bounded but still consumes CPU, memory and temporary disk space.
- The project does not provide live packet capture, prevention/blocking, public deployment hardening, or generalization guarantees.
- Uploaded data and experiment results should be handled according to your institutional policies; do not commit raw captures, model artifacts, generated reports or secrets to Git.

## Reporting an issue responsibly

If GitHub private vulnerability reporting is enabled for this repository, use that channel. Otherwise, contact the repository maintainer through an established private channel; do not publish exploit details, credentials, or private traffic data in a public issue.

For non-sensitive bugs, open a GitHub issue with a synthetic reproducer, expected behavior and observed behavior. Do not provide real network identifiers, private capture files or secrets.

## Scientific limitations

Held-out CIC-IDS2017 results are from a same-capture scenario, not proof of unseen-network performance. DDoS probabilities are uncalibrated and SHAP attributions describe model behavior rather than causal evidence of attacks.
