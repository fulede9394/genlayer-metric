# Test cases (run in GenLayer Studio / direct tests)

## Deterministic — no web or LLM needed
1. Valid request -> id 0, count 1, PENDING, `is_verified(0)` is false.
2. Tolerance 99 bps or 1001 bps -> rejected; 100 and 1000 accepted.
3. Non-https source -> rejected.
4. Field description shorter than 10 chars -> rejected.
5. `get_metric(99)` / verifying an unknown id -> rejected.
6. Verifying the same request twice -> second call rejected.

## Tolerance arithmetic (checked locally, no floats)
7. Leader 100000, validator 101500, tolerance 200 bps (2%) -> accept
   (1500 * 10000 = 15,000,000 <= 100000 * 200 = 20,000,000).
8. Leader 100000, validator 103000, tolerance 200 bps -> reject
   (3000 * 10000 = 30,000,000 > 20,000,000).
9. Leader 0, validator 0 -> accept; leader 0, validator 1 -> reject.

## Non-deterministic — on-chain behaviour
10. Real GitHub API star count, 2% tolerance -> VERIFIED with a
    positive integer value. If validators read outside the band,
    the call does not finalise and the request stays PENDING —
    no wrong value is stored.
