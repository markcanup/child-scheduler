# TASKS.md

## Project Goal

Build the AWS side of the Child Scheduler system.

- Hubitat is the local execution engine
- AWS is the source of truth and scheduler/compiler
- UI is a React web app hosted in AWS
- Backend is API Gateway + Lambda + DynamoDB
- Auth:
  - Web UI: Cognito JWT
  - Hubitat: shared secret header (`X-Hubitat-Token`)

Codex should work milestone-by-milestone, keep changes small, and avoid speculative refactors.

v1 scope assumption:
- exactly one user and one hub (single-tenant, single-hub)

---

## Repo Structure

Expected repo layout:

    child-scheduler/
      PROJECT_BRIEF.md
      TASKS.md

      backend/
        shared/
        functions/
        tests/

      ui/
        src/

      hubitat/
        ChildSchedulerHub.groovy

      docs/

---

## Ground Rules

1. Read `PROJECT_BRIEF.md` before making changes.
2. Keep backend contracts aligned with `PROJECT_BRIEF.md`.
3. Do not redesign the architecture unless a concrete implementation issue requires it.
4. Prefer small, reviewable commits/patches.
5. Add tests for compiler logic before or alongside compiler implementation.
6. Treat DynamoDB as the persistence model already decided:
   - `ActionCatalogs`
   - `Schedules`
7. Keep the first implementation simple:
   - full replace on `PUT /schedule/config`
   - 7-day compile window
   - no GSIs initially
8. Use repo-local Codex guidance/config if added later.
9. Use optimistic locking with `scheduleVersion` where practical; concurrency risk is minimal in v1.
   - `scheduleVersion` must increment on every recompile.
10. Set `META.timezone = "America/New_York"` for v1.
11. Use the common error contract:
    ```json
    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable explanation"
      }
    }
    ```

---

## Milestone 0 — Bootstrap backend project

### Goal
Create the backend project skeleton and shared utilities.

### Tasks
- Create `backend/` project structure
- Choose implementation language:
  - prefer Python
- Create shared modules:
  - `shared/auth.py`
  - `shared/responses.py`
  - `shared/dynamodb.py`
  - `shared/catalog.py`
  - `shared/validation.py`
  - `shared/dates.py`
  - `shared/compiler.py`
- Create Lambda handler folders:
  - `functions/hubitat_action_catalog_post/`
  - `functions/catalog_get/`
  - `functions/schedule_config_get/`
  - `functions/schedule_config_put/`
  - `functions/hubitat_schedule_get/`
- Add a basic local test setup under `backend/tests/`
- Add a backend README with local run/test instructions

### Deliverable
A compilable backend skeleton with placeholder handlers and shared utility modules.

---

## Milestone 1 — Implement `POST /hubitat/action-catalog`

### Goal
Allow Hubitat to push the action catalog into DynamoDB.

### Endpoint
`POST /hubitat/action-catalog`

### Tasks
- Implement handler: `hubitat_action_catalog_post`
- Validate required request fields:
  - `hubId`
  - `generatedAt`
  - `catalogVersion`
  - `actionDefinitions`
  - `resources`
- Validate uniqueness of `resourceId` within payload
- Build `resourceIndex` from `resources`
- Upsert into `ActionCatalogs`
- Trigger `compile_schedule(...)` after successful catalog write so schedule reflects new catalog validity immediately
- Return:
  - `hubId`
  - `status`
  - `receivedAt`
  - `resourceCount`
- Implement Hubitat shared-secret validation using `X-Hubitat-Token`
- Add tests for:
  - happy path
  - missing required fields
  - duplicate resource IDs
  - invalid token
  - recompilation triggered on catalog change

### Deliverable
Working Lambda for catalog upsert with tests.

---

## Milestone 2 — Implement `GET /catalog`

### Goal
Allow the UI to retrieve the latest action catalog.

### Endpoint
`GET /catalog`

### Tasks
- Implement handler: `catalog_get`
- Load current hub’s `ActionCatalogs` item
- Return:
  - `hubId`
  - `generatedAt`
  - `catalogVersion`
  - `actionDefinitions`
  - `resources`
- Add auth stub or integration point for Cognito/JWT
- For now, allow hub resolution to be mocked/configured if full Cognito integration is not yet wired
- Add tests for:
  - catalog exists
  - catalog missing
  - unauthorized request

### Deliverable
Working Lambda for reading the action catalog.

---

## Milestone 3 — Implement `GET /schedule/config` (read-only first)

### Goal
Allow the UI to load current schedule config plus preview/broken references.

### Endpoint
`GET /schedule/config`

### Tasks
- Implement handler: `schedule_config_get`
- Read from `Schedules`:
  - `META`
  - `DEF#...`
  - `DAY#...`
  - preview window `EVT#...`
  - preview window `BROKEN#...`
- Return grouped response:
  - `hubId`
  - `meta`
  - `scheduleDefinitions`
  - `dayConfigs`
  - `compiledPreview`
  - `brokenReferences`
- If no data exists yet:
  - return sensible empty defaults
- Add tests for:
  - empty hub state
  - populated hub state
  - unauthorized request

### Deliverable
Working read endpoint for schedule config.

---

## Milestone 4 — Build compiler as pure functions with tests

### Goal
Implement the schedule compiler independently of Lambda wiring first.

### Tasks
Implement in `shared/compiler.py`:

- `validate_schedule_definitions(...)`
- `validate_day_configs(...)`
- `build_catalog_index(...)`
- `build_compile_dates(...)`
- `build_effective_day_config(...)`
- `get_applicable_schedule_definitions(...)`
- `resolve_times_for_date(...)`
- `validate_resolved_action(...)`
- `build_meta_item(...)`
- `build_definition_item(...)`
- `build_day_item(...)`
- `build_compiled_event_item(...)`
- `build_broken_item(...)`
- `compile_schedule(...)`

### Test cases
Add tests for:

#### Validation
- duplicate `scheduleId`
- invalid `timeMode`
- invalid `actionType`
- missing required fields
- relative reference to missing schedule

#### Time resolution
- absolute schedules
- relative schedules
- chained relative schedules
- disabled schedules
- day override with `timeOverride`
- day override with `enabled = false`
- circular dependency detection
- circular dependency emits common error shape

#### Action validation
- valid `rule`
- valid `speech`
- valid `notify`
- missing catalog resource
- wrong resource type
- missing `text`
- empty `targetIds`

#### Compile output
- correct `EVT#...` items generated
- correct `BROKEN#...` items generated
- correct preview arrays returned

### Deliverable
Fully tested compiler module.

---

## Milestone 5 — Implement `PUT /schedule/config`

### Goal
Save editable schedule config and compile the next 7 days.

### Endpoint
`PUT /schedule/config`

### Tasks
- Implement handler: `schedule_config_put`
- Validate request payload:
  - `hubId`
  - `meta`
  - `scheduleDefinitions`
  - `dayConfigs`
- Load current `ActionCatalogs` item
- Load current `META` item
- Determine next `scheduleVersion`
- Call `compile_schedule(...)`
- Apply optimistic locking via `scheduleVersion` check (best-effort; low contention expected in v1)
- Increment `scheduleVersion` on every recompile
- Replace current editable config:
  - delete existing `DEF#...`
  - write new `DEF#...`
  - delete existing `DAY#...`
  - write new `DAY#...`
- Replace current compiled 7-day window:
  - delete existing `EVT#...` in window
  - delete existing `BROKEN#...` in window
  - write new `EVT#...`
  - write new `BROKEN#...`
- Upsert new `META`
  - include `timezone = "America/New_York"`
- Return:
  - `hubId`
  - `status`
  - `scheduleVersion`
  - `compiledAt`
  - `compiledPreview`
  - `brokenReferences`

### Tests
- full happy path
- validation failure
- no action catalog present
- broken references generated
- relative schedule compilation
- overwrite of previous window

### Deliverable
Working save-and-compile endpoint.

---

## Milestone 6 — Implement `GET /hubitat/schedule`

### Goal
Allow Hubitat to pull the compiled schedule for the next N days.

### Endpoint
`GET /hubitat/schedule?hubId=...&days=7`

### Tasks
- Implement handler: `hubitat_schedule_get`
- Validate Hubitat shared secret
- Validate `days` query:
  - integer only
  - min 1
  - max 90
- Read:
  - `META`
  - `EVT#...` in requested window
  - `BROKEN#...` in requested window
- Transform items into Hubitat response contract:
  - compiled events
  - broken events with `validation` block
- Sort by:
  - date
  - time
  - eventId
- Return:
  - `hubId`
  - `generatedAt`
  - `scheduleVersion`
  - `timezone`
  - `events`
- Response window semantics:
  - day-based window starting with current day in `META.timezone` as day 1
  - include full-day events for each included day
  - include already-past events from today

### Tests
- compiled events only
- compiled + broken events
- empty result
- invalid token
- invalid/missing hubId
- invalid `days` values (non-integer, <1, >90)
- includes past events from current day

### Deliverable
Working Hubitat schedule pull endpoint.

---

## Milestone 7 — API Gateway wiring and environment config

### Goal
Deploy backend routes cleanly.

### Tasks
- Define/deploy API Gateway HTTP API routes:
  - `POST /hubitat/action-catalog`
  - `GET /hubitat/schedule`
  - `GET /catalog`
  - `GET /schedule/config`
  - `PUT /schedule/config`
- Add environment variable handling for:
  - DynamoDB table names
  - allowed origin(s)
- Add basic CORS for browser routes
- Add deployment docs
  - document PSK storage on AWS side backing the UI preference/profile field
  - document annual PSK rotation process
  - document UI-only 365-day key-age warning mechanism (non-breaking)

### Deliverable
Deployed backend API skeleton with routes mapped to Lambdas.

---

## Milestone 8 — Minimal UI bootstrap

### Goal
Create a thin UI that can consume real backend data.

### Tasks
- Create React app in `ui/`
- Add app shell
- Add data service layer for:
  - `GET /catalog`
  - `GET /schedule/config`
  - `PUT /schedule/config`
- Create initial pages/components:
  - login placeholder
  - catalog status/debug page
  - schedule config viewer
  - save config action
  - profile/preferences section for Hubitat PSK
  - visible PSK last-rotated timestamp
- Do not over-polish UI yet

### Deliverable
Minimal UI that can load and save schedule data.

---

## Milestone 9 — Cognito integration

### Goal
Secure browser-facing endpoints.

### Tasks
- Add Cognito setup docs
- Add frontend auth flow
- Wire JWT auth into browser routes
- Ensure Hubitat routes remain on shared-secret auth path
- Add authenticated UI flow for viewing/updating Hubitat PSK profile field
- Add notes for local development vs deployed environments

### Deliverable
Authenticated UI flow and secured browser API access.

---

## Milestone 10 — End-to-end integration with Hubitat

### Goal
Connect real Hubitat to real AWS backend.

### Tasks
- Point Hubitat app at deployed API
- Test:
  - catalog push
  - catalog retrieval in UI
  - save config in UI
  - compile in backend
  - Hubitat schedule pull
  - actual local execution from Hubitat
- Fix contract mismatches if any
- Update docs with real deployment/config steps

### Deliverable
Working end-to-end system.

---

## Milestone 11 — Cleanup and hardening

### Goal
Make the system maintainable.

### Tasks
- Improve error handling
- Add structured logging
- Add input sanitization for `text` fields
- Add duplicate-notification suppression strategy for broken references
  - v1 dedupe key: `sourceScheduleId + date`
- Add admin notification separation if not already implemented
- Add retry-safe/idempotent behavior where useful
- Improve docs

### Deliverable
Stable v1 backend + UI + Hubitat integration.

---

## Testing Priorities

Codex should prioritize tests for:
1. compiler logic
2. endpoint request validation
3. DynamoDB item mapping
4. Hubitat contract formatting

---

## Non-Goals for v1

Do not add these unless explicitly requested:
- partial update endpoints
- background job system
- advanced RBAC
- multi-hub multi-tenant complexity
- historical analytics
- GraphQL
- aggressive single-table DynamoDB redesign
- extra AWS services unless needed

Note: DynamoDB volume is expected to be very low in v1 (single user/hub), reinforcing no-GSI baseline.

---

## First Task for Codex

Start with:

1. Read `PROJECT_BRIEF.md` and this file
2. Restate the architecture in a short summary
3. Create backend project skeleton (Milestone 0)
4. Implement `POST /hubitat/action-catalog` and its tests (Milestone 1)
5. Stop and summarize changes made
