# UI (Milestones 8-9 bootstrap)

Minimal React + Vite UI scaffold that can call backend APIs and use Cognito-backed JWT auth.

## Features

- App shell
- Cognito login section (Hosted UI URL generation)
- Token capture from Cognito redirect hash (`id_token` / `access_token`)
- Local token paste fallback for development
- Catalog status/debug panel (`GET /catalog`)
- Schedule config viewer/editor (`GET /schedule/config`, `PUT /schedule/config`)
- Authenticated profile/preferences flow for Hubitat PSK + last-rotated timestamp (local storage placeholder)
- Non-blocking warning when PSK age reaches 365+ days

## Run locally

```bash
cd ui
npm run dev
```

> Dependencies are expected to be preinstalled in this environment.

## Environment

- `VITE_API_BASE_URL` (default: `http://localhost:3001`)
- `VITE_DEFAULT_HUB_ID` (default: `default-hub`)
- `VITE_COGNITO_DOMAIN` (optional; example `https://your-domain.auth.us-east-1.amazoncognito.com`)
- `VITE_COGNITO_CLIENT_ID` (optional; Cognito app client id)
- `VITE_COGNITO_REDIRECT_URI` (optional; defaults to `window.location.origin`)
- `VITE_COGNITO_LOGOUT_URI` (optional; defaults to `window.location.origin`)

## Local development auth notes

- If backend is running with `UI_JWT_STUB_TOKEN`, paste that token in the UI login panel and click **Use pasted token**.
- If deployed with Cognito authorizer enabled, use **Sign in with Cognito Hosted UI** and the UI will capture the token from redirect.
