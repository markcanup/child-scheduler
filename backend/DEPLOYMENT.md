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

Recommended guided answers:

- Stack Name: `child-scheduler-backend`
- AWS Region: your target region
- Parameter `StageName`: `prod` (or environment-specific stage)
- Parameter `ActionCatalogsTableName`: DynamoDB table name for catalogs
- Parameter `SchedulesTableName`: DynamoDB table name for schedule data
- Parameter `AllowedOrigins`: comma-separated browser origins
  - Example: `https://app.example.com,http://localhost:5173`
- Parameter `HubitatToken`: current Hubitat PSK
- Parameter `HubitatTokenLastRotated`: PSK last-rotated timestamp in `YYYY-MM-DD.HH:MM:SS` (UTC) format (example: `2026-04-23.18:20:12`)

Milestone 9 parameters for Cognito JWT browser auth:

- Parameter `CognitoIssuerUrl`: `https://cognito-idp.<region>.amazonaws.com/<userPoolId>`
- Parameter `CognitoAppClientId`: Cognito app client id

Browser routes now require Cognito JWT validation. If Cognito params are omitted/empty, browser-route requests are rejected with `401 UNAUTHORIZED`.

## 3) Route mapping

The HTTP API exposes:

- `POST /hubitat/action-catalog` (Hubitat shared-secret auth)
- `GET /hubitat/schedule` (Hubitat shared-secret auth)
- `GET /catalog` (browser JWT auth)
- `GET /schedule/config` (browser JWT auth)
- `PUT /schedule/config` (browser JWT auth)

## 4) Environment parameters used by Lambdas

`template.yaml` wires parameters into Lambda environment variables:

- `ACTION_CATALOGS_TABLE`
- `SCHEDULES_TABLE`
- `HUBITAT_TOKEN`
- `HUBITAT_TOKEN_LAST_ROTATED`
- `DEFAULT_HUB_ID`
- `COGNITO_ISSUER_URL`
- `COGNITO_APP_CLIENT_ID`
- `ALLOWED_ORIGINS`

## 5) CORS behavior

CORS is configured at the API Gateway HTTP API level.

- `AllowedOrigins` controls allowed browser origins and is injected into Lambda env for diagnostics.
- Lambda responses include `X-Cors-Origin-Matched` and `X-Cors-Allowed-Origins` headers to improve debugging when the browser reports a generic "failed to fetch" CORS error.
- Unauthorized browser responses include structured `error.details.cors` diagnostics.
- Allowed methods: `GET`, `PUT`, `POST`, `OPTIONS`
- Allowed headers: `Authorization`, `Content-Type`

## 6) Cognito docs

See `backend/COGNITO_SETUP.md` for detailed setup steps and local-vs-deployed notes.

## 7) PSK operational policy (v1)

### Storage + rotation source of truth

- Hubitat shared secret is managed as Lambda/SAM deployment configuration (`HUBITAT_TOKEN`), not via UI profile editing.
- Rotation timestamp is managed via `HUBITAT_TOKEN_LAST_ROTATED`.
- Store both values in secure deployment inputs (for example, GitHub Actions secrets/vars + SAM parameters), and never log the token.

### Rotation

- Rotate PSK annually.
- Rotation process:
  1. Generate a new PSK.
  2. Update deployment secret/parameter for `HUBITAT_TOKEN`.
  3. Update deployment parameter for `HUBITAT_TOKEN_LAST_ROTATED` using `YYYY-MM-DD.HH:MM:SS` (UTC).
  4. Deploy SAM.
  5. Update Hubitat app config to match.
  6. Verify `POST /hubitat/action-catalog` and `GET /hubitat/schedule` authentication succeeds.

### UI key-age warning

- UI surfaces a non-blocking warning when `HUBITAT_TOKEN_LAST_ROTATED` age reaches **365 days**.
- Warning does not block API calls.
