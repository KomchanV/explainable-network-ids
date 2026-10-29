# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha.1] - 2026-10-30

### Added

- Offline BENIGN-versus-DDoS training and evaluation on network-flow CSV data.
- Batch prediction with saved-schema validation and row-order preservation.
- Streamlit dashboard for local inference, metrics, downloads, and SHAP views.
- Global and local SHAP explanations with probability reconstruction checks.
- Deterministic synthetic smoke fixtures and a documented CIC-IDS2017 workflow.
- Automated tests for data validation, leakage controls, persistence, inference,
  explanations, comparison reporting, and dashboard behavior.
- Reproducibility scripts and documented real-data experiment results.

### Security

- Raw datasets, trained models, generated reports, environment files, caches,
  and local virtual environments are excluded from version control.
