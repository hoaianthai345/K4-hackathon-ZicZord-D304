# Discord scope and ingestion model

## Entity graph

```text
Cohort K4
├── common channels: announcement, general, QA, sharing
├── Group G10
│   ├── mentor
│   ├── Team T004
│   │   └── four students
│   └── Team T009
├── lecture rooms
│   └── Lec-D302
└── lab rooms
    └── Lab-D304
```

A student can belong to one team, one mentor group, one lecture room, one lab room and the cohort.

## Authorization flow

```text
user_id
→ lookup trusted membership
→ compute allowed scope keys
→ filter visible channels
→ filter source messages
→ recall only allowed memory banks
→ compose answer with source citations
```

Scope list is never accepted from the browser.

## Ingestion flow

```text
Apify Dataset API
→ normalize actor-specific fields
→ resolve Discord channel to internal channel
→ unknown channel: skip
→ resolve known author when possible
→ deduplicate by source_message_id
→ persist source message and permalink
```

Bearer token stays server-side. The adapter uses offset and limit pagination and `clean=1`.

## Write permissions

| Scope | Student | Mentor |
|---|---|---|
| Own user | Confirm, edit, delete | Own user only |
| Own team | Confirm, edit, delete | No team membership in MVP |
| Group | Read | Confirm, edit, delete |
| Room | Read | Confirm, edit, delete |
| Cohort | Read | Confirm, edit, delete |

## Threat cases

1. User changes `team_id` in request: ignored because membership comes from server seed/store.
2. Apify item has unknown channel: skipped.
3. T009 asks about T004: no T004 channel or bank enters retrieval.
4. Candidate is confirmed by another user: `403`.
5. Actor field shape changes: item is skipped unless required normalized fields exist.
