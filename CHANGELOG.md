# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2026-06-15
- Fix: Auto-verify users when `EMAIL_TEST_MODE=true` to allow CI E2E to log in.
- Fix: Use demo user email in `verify_demo.ps1` when creating cardholder during E2E.
- Add: `/api/financial-accounts` endpoint to support E2E balance checks.
- CI: Windows E2E workflow improvements and mock Lithic support.
 - Security: Gate test auto-verify behind `ALLOW_AUTO_VERIFY` env var; E2E workflow sets this variable.
