# UI (Milestones 8-9)

Minimal React + Vite UI scaffold that can call backend APIs and use Cognito-backed JWT auth.

## Features

- App shell
- Cognito login section (Hosted UI URL generation)
- OAuth authorization code exchange against Cognito `/oauth2/token`
- Token capture from Cognito redirect hash (`id_token` / `access_token`) for compatibility
- Local token paste fallback for development
- Catalog status/debug panel (`GET /catalog`)
- Schedule config viewer/editor (`GET /schedule/config`, `PUT /schedule/config`)
- Authenticated profile/preferences flow for Hubitat PSK + last-rotated timestamp (local storage placeholder)
- Non-blocking warning when PSK age reaches 365+ days
- Request failure diagnostics panel for network and HTTP errors (URL, method, status, response body when available)

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
- `VITE_COGNITO_REDIRECT_URI` (optional; defaults to `window.location.origin`, e.g. `https://ubuntu24.lan:5179`)
- `VITE_COGNITO_LOGOUT_URI` (optional; defaults to `window.location.origin`)

## Local development auth notes

- If backend is running with `UI_JWT_STUB_TOKEN`, paste that token in the UI login panel and click **Use pasted token**.
- If deployed with Cognito authorizer enabled, use **Sign in with Cognito Hosted UI** and the UI exchanges `?code=...` using PKCE (`code_verifier`) at `https://<domain>/oauth2/token`.
