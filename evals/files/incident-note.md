## INC-4471 — duplicate charges on checkout (draft notes from on-call)

Between 14:02 and 14:19 UTC, 37 customers were charged twice for one order.
Both charges carry the same idempotency key in the payment-gateway logs.

What we know:
- The order service retries the charge call when the gateway does not answer within 3 s.
- Gateway p99 latency rose to 4.1 s in the same window.
- The dedup table write and the gateway call are not in one transaction.

Current theory: the duplicates may be caused by a race condition between the retry and the
dedup-table write, but we have not reproduced it yet. It could also be a gateway-side bug
in idempotency-key handling; the gateway vendor has not replied.

Next: try to reproduce in staging with injected 4 s gateway latency.
