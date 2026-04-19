# Deployment Guide

This backend is deployed with AWS SAM from `backend/template.yaml`.

## 1) Prerequisites

- AWS account + IAM permissions for Lambda, API Gateway HTTP API, CloudFormation, and DynamoDB.
- AWS SAM CLI installed.
- Two DynamoDB tables created:
  - `ActionCatalogs` (`PK: hubId`)
  - `Schedules` (`PK: hubId`, `SK: itemKey`)

## 2) Build and deploy

From `backend/`:

```bash
sam build
sam deploy --guided
```

Recommended guided answers for Milestone 7:

- Stack Name: `child-scheduler-backend`
- AWS Region: your target region
- Parameter `StageName`: `prod` (or environment-specific stage)
- Parameter `ActionCatalogsTableName`: DynamoDB table name for catalogs
- Parameter `SchedulesTableName`: DynamoDB table name for schedule data
- Parameter `AllowedOrigins`: comma-separated browser origins
  - Example: `https://app.example.com,http://localhost:3000`
- Parameter `HubitatToken`: current Hubitat PSK

## 3) Route mapping

The HTTP API exposes:

- `POST /hubitat/action-catalog`
- `GET /hubitat/schedule`
- `GET /catalog`
- `GET /schedule/config`
- `PUT /schedule/config`

## 4) Environment parameters used by Lambdas

`template.yaml` wires parameters into Lambda environment variables:

- `ACTION_CATALOGS_TABLE`
- `SCHEDULES_TABLE`
- `HUBITAT_TOKEN`
- `UI_JWT_STUB_TOKEN`
- `DEFAULT_HUB_ID`

## 5) CORS behavior

CORS is configured at the API Gateway HTTP API level.

- `AllowedOrigins` controls allowed browser origins.
- Allowed methods: `GET`, `PUT`, `POST`, `OPTIONS`
- Allowed headers: `Authorization`, `Content-Type`

Hubitat routes do not require CORS behavior because they are not browser calls, but they are still covered by this API-level setting.

## 6) PSK operational policy (v1)

The project brief requires managing the Hubitat PSK via AWS-backed UI profile preferences.

### Storage

- PSK must be persisted in an AWS-backed user profile/preferences store used by the UI.
- Current Lambda auth uses `HUBITAT_TOKEN`; treat this as bootstrap/runtime wiring until UI profile-backed PSK plumbing is implemented.
- Store PSK encrypted at rest (for example, KMS-backed encryption) and never log it.

### Rotation

- Rotate PSK annually.
- Rotation process:
  1. Generate a new PSK.
  2. Update PSK in the UI preference/profile field.
  3. Update Hubitat app config to match.
  4. Verify `POST /hubitat/action-catalog` and `GET /hubitat/schedule` authentication succeeds.
  5. Record rotation timestamp in profile metadata.

### UI-only key-age warning

- UI should surface a non-blocking warning when PSK age reaches **365 days**.
- The warning should not block API calls by itself.
- Show both:
  - last rotated timestamp
  - days since rotation

This warning is informational and supports annual rotation hygiene.
