# Risky SaaS

This synthetic application is the deterministic ChangeProof demo fixture. It contains no real customer data or credentials.

## Intentional migration risks

1. `001_drop_legacy_status.sql` removes a column still read by the order service.
2. `002_shrink_email.sql` narrows email storage below values in `seed.sql`.
3. `003_unsafe_not_null.sql` makes existing nullable data invalid without a default.
4. `004_drop_payments.sql` destructively removes a table without a rollback migration.

These defects are intentional. Do not "fix" them in the sample; future ChangeProof phases use them as known-positive validation cases.
