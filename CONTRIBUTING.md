# Contributing to Samoyed

Samoyed is a configurable research-assistant framework. Keep provider integrations replaceable, keep source attribution intact, and do not add real private Lab data to fixtures, screenshots, seed files, or documentation.

Before submitting a change:

- run the API test suite from `services/api`;
- run the web checks from `apps/web`;
- run `git diff --check`;
- confirm that secrets and downloaded private content are not included.

When changing AI behavior, include the expected fallback behavior and make clear whether the result came from an AI provider, web retrieval, or local rules.
