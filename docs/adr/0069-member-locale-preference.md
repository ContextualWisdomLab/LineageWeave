# ADR 0069: Persist the Buyer locale on the member account

- Status: Accepted
- Date: 2026-08-19

## Decision

The authenticated member's Buyer locale is stored as `user_account.preferred_locale`
with the product's five-value constraint: `en`, `ko`, `zh`, `ja`, or `vi`.
The GNB selector updates both the local display and the authenticated member
preference through `/api/me/preferences`. On login, the server preference wins
over browser detection; browser storage remains only the unauthenticated or
offline fallback.

## Consequences

- A member's choice survives reloads and different browsers after login.
- The preference is account-scoped and is not mixed into post or session keys.
- Invalid locale values are rejected at the API and database boundaries.
