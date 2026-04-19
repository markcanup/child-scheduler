# UI (Milestone 8 bootstrap)

Minimal React + Vite UI scaffold that can call the backend API.

## Features

- App shell
- Login placeholder section
- Catalog status/debug panel (`GET /catalog`)
- Schedule config viewer/editor (`GET /schedule/config`, `PUT /schedule/config`)
- Profile/preferences placeholder for Hubitat PSK and last-rotated timestamp
- Non-blocking warning when PSK age reaches 365+ days

## Run locally

```bash
cd ui
npm install
npm run dev
```

## Environment

- `VITE_API_BASE_URL` (default: `http://localhost:3001`)
- `VITE_DEFAULT_HUB_ID` (default: `default-hub`)
