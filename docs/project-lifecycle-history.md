# Project lifecycle history

Open a source post that contains explicit or semantic project evidence. The
post detail displays **Project lifecycle history** when that project has
visible lifecycle records.

## What the Buyer can do

1. Select a project when the source post refers to more than one project.
2. Select an order, specification change, delivery, VOC, or rebid event by
   mouse or keyboard.
3. Open the exact source post supporting the selected event or relation.
4. Read responsibility intervals and visible handover-evidence gaps.
5. Detect that the response is truncated before treating it as complete.

## Evidence behavior

The endpoint is `GET /api/projects/{project_key}/history`. It returns only
source-post-backed records that pass the caller's existing RBAC, corporate
visibility, draft, and deletion checks. If an event endpoint is hidden, its
relations are omitted as well. A hidden assignment is not named and does not
contribute its dates to the gap calculation.

`related_to` and `follows` are displayed as recorded associations. They are not
renamed as causes. Empty or unavailable states stay empty; the UI does not
invent project events, people, dates, evidence counts, or relations.

## Synthetic demonstration

`make seed` now runs `scripts/seed_project_history.py` after the existing Demo
Corp seed and creates project `P-1042` with order, specification, delivery,
VOC, rebid, and three synthetic responsibility assignments. No production or
customer data is committed.
