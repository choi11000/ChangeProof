# Demo Scenario

## Final proof moment

After the original dropped-column fixture produces SQLSTATE `42703` and `PROVEN_FAIL`, select **Verify remediation**. The server authoritatively reruns the original subject, applies the allowlisted compatibility migration that preserves `legacy_status`, and executes the same verification query. The proof is `PROVEN_FIXED` only when the contract digest is identical, the subject digest changed, and the remediated run is `PROVEN_PASS`.

The UI states: “Failure reproduced before remediation. The same experiment passed after remediation.” This claim applies only to the controlled experiment.

The synthetic `samples/risky-saas` repository supplies deterministic known-positive cases for the ChangeProof demo.

## Baseline

The schema contains users, orders, payments, and subscriptions. Seed data includes an email longer than 30 characters and a user whose phone is null. Application code still reads `Order.legacy_status`.

## Risk cases

| Migration | Expected finding | Future validation evidence |
| --- | --- | --- |
| Drop `orders.legacy_status` | Application/schema mismatch | Source reference in `order_service.py` |
| Shrink `users.email` to 30 | Data incompatibility | `MAX(length(email))` exceeds 30 |
| Set `users.phone` NOT NULL | Existing null data | Null-count query returns at least one row |
| Drop `payments` | Destructive migration | AST operation and missing rollback |

Phase 2 proves these changes can be parsed into typed facts. Later phases add dependency search, sandbox execution, evidence, scoring, remediation, and re-validation in that order.
