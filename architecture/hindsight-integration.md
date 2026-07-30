# Hindsight integration: scoped Discord memory

Upstream: <https://github.com/vectorize-io/hindsight>
Version: `0.8.6`
Decision: one bank per authorization scope.

## Bank contract

```text
kute-<scope_type>-<scope_id>
```

Examples:

```text
kute-user-u01862
kute-team-t004
kute-group-g10
kute-room-lec-d302
kute-room-lab-d304
kute-cohort-k4
```

Bank IDs are created on the backend. Browser clients never provide arbitrary bank IDs.

## Confirmed memory

```json
{
  "bank_id": "kute-team-t004",
  "document_id": "mem-team-t004-stack",
  "content": "T004 dùng Next.js, FastAPI, Docker và Apify.",
  "tags": [
    "scope_type:team",
    "scope_id:T004",
    "layer:canonical",
    "status:confirmed",
    "kind:decision"
  ]
}
```

Candidate remains in app state with `status:proposed`. Confirm retains it as canonical. Delete calls Hindsight document deletion.

## Recall contract

FastAPI computes all allowed `(scope_type, scope_id)` pairs from membership. It recalls allowed banks in parallel with:

```text
scope_type:<type>
scope_id:<id>
layer:canonical
status:confirmed
tags_match=all_strict
```

Results are merged and deduplicated. T004 never queries `kute-team-t009`.

## Fallback

JSON store remains the source of truth so the hackathon demo works without an LLM key. Health reports:

- `local-demo`
- `hindsight`
- `hindsight-fallback`

## Exit criteria

- Confirmed memory can be retained and recalled from its scope bank.
- Proposed memory is not recalled.
- Cross-team bank is never requested.
- Delete removes the matching Hindsight document.
- Provider failure does not break the local demo.
