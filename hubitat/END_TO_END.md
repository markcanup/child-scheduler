# Hubitat ↔ AWS end-to-end integration (Milestone 10)

This guide documents the real integration path between the Hubitat app (`hubitat/ChildSchedulerHub.groovy`) and the deployed AWS backend routes.

## 1) Prerequisites

- Backend deployed (see `backend/DEPLOYMENT.md`).
- DynamoDB tables configured and Lambda routes healthy.
- Hubitat app installed from `hubitat/ChildSchedulerHub.groovy`.
- Matching shared secret configured in both places:
  - AWS backend parameter/environment: `HUBITAT_TOKEN`
  - Hubitat app setting: **Hubitat shared secret (X-Hubitat-Token)**

## 2) Hubitat app settings

In Hubitat app preferences:

- `AWS Base URL`: API base URL (for example `https://abc123.execute-api.us-east-1.amazonaws.com`)
- `Hub ID`: same hub id expected by backend/UI
- `Hubitat shared secret (X-Hubitat-Token)`: must match backend token exactly
- `Days of schedule to pull`: typically `7`
- Optional:
  - Enable `Push catalog on initialize`
  - Enable `Pull schedule on initialize`

## 3) End-to-end verification sequence

### Step A — Catalog push from Hubitat

1. Press **Push action catalog now** in Hubitat app.
2. Confirm Hubitat state page shows `Last catalog push status: HTTP 200`.
3. Confirm backend receives `resources` with contract shape:
   - `resourceId`
   - `type` (`rule`, `speechTarget`, `notifyDevice`)
   - `label`

### Step B — Catalog retrieval in UI

1. Open UI.
2. Load catalog from `GET /catalog`.
3. Verify catalog data appears and contains resources pushed by Hubitat.

### Step C — Save config in UI (compile trigger)

1. Create or update schedule config in UI.
2. Save via `PUT /schedule/config`.
3. Confirm response includes incremented `scheduleVersion` and preview output.

### Step D — Hubitat schedule pull

1. Press **Pull schedule now** in Hubitat app.
2. Confirm Hubitat state page shows:
   - `Last schedule pull status: HTTP 200`
   - `Last schedule version` updated
3. Confirm events are scheduled (`Pending scheduled events count > 0` when applicable).

### Step E — Local execution in Hubitat

1. Wait for the next scheduled event time.
2. Verify expected local behavior:
   - Rule action executes via Rule Machine call.
   - Speech action calls `speak`.
   - Notify action calls `deviceNotification`.

## 4) Common mismatch checks

- **401 from Hubitat routes**:
  - Verify Hubitat shared secret exactly matches backend `HUBITAT_TOKEN`.
- **Catalog accepted but events become broken**:
  - Verify catalog resources use `type` values expected by backend compiler:
    - `rule`
    - `speechTarget`
    - `notifyDevice`
- **No events execute**:
  - Check Hubitat logs for validation skips or missing device/rule references.
  - Confirm pulled event date/time is in the future at pull time.

## 5) Operational notes

- Re-push catalog whenever allowed rules/devices change.
- Re-run pull after config save when testing manually.
- Keep PSK rotation aligned with the annual policy in `backend/DEPLOYMENT.md`.
