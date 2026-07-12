# Privacy and data lifecycle

Samoyed separates shared research data from account data:

- Lab profiles, memberships, watchlists, source metadata and interpretations are scoped by `lab_id`.
- When OAuth is enabled, Lab endpoints require an active membership or system-admin role.
- `DELETE /api/auth/me/data` removes the signed-in user's account, memberships and audit actor references. Shared Lab research data is not deleted by this operation.
- Administrators can delete a Lab or source through the existing admin endpoints. Deleting a Lab removes its memberships, invitations, profile, watchlist links and Lab interpretations.
- Providers receive only the prompt, selected source text and configured Lab context needed for the requested operation. Do not put secrets or private credentials in Lab profiles or source content.

Before deploying, configure database backups, retention, access logging, HTTPS-only cookies and a provider-specific data-processing agreement where required.
