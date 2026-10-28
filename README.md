# PublicMetric — Tolerance-Based Public Numeric Metric Oracle

A standalone Intelligent Contract that puts a public number on-chain
without pretending validators will read it byte-identically.

## Why this exists

A repo's star count, a project's download total, a registry's entry
count — these numbers are useful on-chain (grants, rankings, release
gates), but they move between validator runs. Exact equality rejects
honest readings that differ by a handful of units, and free-form LLM
agreement accepts anything that sounds close. PublicMetric makes the
tolerance explicit, in the request itself.

1. `request_metric(name, source_url, field, tolerance_bps)` — the
   source, the number to read, and the tolerance (100–1000 bps, i.e.
   1%–10%) are fixed at request time.
2. `verify_metric(request_id)` — the leader extracts digits only.
   Each validator re-reads the number and accepts it only if it falls
   inside the tolerance band.
3. The stored value is an integer (`u256`); no floats, no free text.

## The validator rule, in code not prose

`gl.vm.run_nondet_unsafe` with a custom validator function:

```
|leader - validator| * 10000 <= leader * tolerance_bps
```

Integer cross-multiplication, no floating point, no rounding debate.
The LLM only extracts digits — it never decides whether the value is
acceptable. That decision is the validator function, and it is
deterministic. If validators disagree outside the band, the transaction
does not finalise and the request stays PENDING: a failed consensus is
never silently stored as a wrong number.

## State design

One-way state machine per request: `PENDING -> VERIFIED`. There is no
re-verify and no edit path. A fresh reading needs a fresh request, so
the history of verified values is append-only.

## Try it in GenLayer Studio

1. Paste `contracts/public_metric.py` into Studio and deploy (no args).
2. `request_metric` with, for example:
   - name: `CPython GitHub stars`
   - source_url: `https://api.github.com/repos/python/cpython`
   - field: `the stargazers_count value in this JSON response`
   - tolerance_bps: `200` (2%)
3. `verify_metric(0)`, then `get_metric(0)` — expect `VERIFIED` and a
   star count in the tens of thousands (the exact figure moves over
   time; that is what the tolerance band is for).

## Tests

See `tests/test_cases.md` (10 cases): tolerance-band arithmetic,
input validation, unknown / double verification, and the
stays-PENDING-on-disagreement behaviour.
