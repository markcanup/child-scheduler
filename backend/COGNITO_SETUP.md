# Cognito setup (Milestone 9)

This project supports Cognito JWT auth for browser-facing routes:

- `GET /catalog`
- `GET /schedule/config`
- `PUT /schedule/config`

Hubitat routes remain protected by `X-Hubitat-Token`:

- `POST /hubitat/action-catalog`
- `GET /hubitat/schedule`

## 1) Create or choose a User Pool

In AWS Cognito:

1. Create/select a User Pool.
2. Create an App Client for the web UI.
3. Configure a Hosted UI domain.
4. Add allowed callback and sign-out URLs (for example your deployed UI URL and local `http://localhost:5173`).
5. In the app client OAuth settings, enable **Authorization code grant**.
6. Ensure scopes include at least `openid`, `email`, and `profile`.

## 2) Capture deploy-time values

You will need:

- **Issuer URL**:
  `https://cognito-idp.<region>.amazonaws.com/<userPoolId>`
- **App client ID**
- **Hosted UI domain URL** for frontend env (`VITE_COGNITO_DOMAIN`)

## 3) Deploy backend with Cognito authorizer enabled

From `backend/`:

```bash
sam build
sam deploy --guided
```

Set these SAM parameters:

- `CognitoIssuerUrl=<issuer URL>`
- `CognitoAppClientId=<app client id>`

If either is empty, API Gateway Cognito JWT authorizer is disabled and route auth falls back to Lambda stub-token validation (`UI_JWT_STUB_TOKEN`) for local development.

## 4) Configure frontend env

For deployed frontend:

- `VITE_API_BASE_URL=<deployed API URL>`
- `VITE_COGNITO_DOMAIN=<hosted ui domain URL>`
- `VITE_COGNITO_CLIENT_ID=<app client id>`
- `VITE_COGNITO_REDIRECT_URI=<frontend URL>`
- `VITE_COGNITO_LOGOUT_URI=<frontend URL>`

Frontend hosted-login behavior:

- Starts auth at:
  `https://<your-domain>.auth.<region>.amazoncognito.com/oauth2/authorize`
- Uses query parameters:
  - `response_type=code`
  - `client_id=<app client id>`
  - `redirect_uri=<VITE_COGNITO_REDIRECT_URI>`
  - `scope=openid email profile`
  - `code_challenge_method=S256` and `code_challenge=<pkce challenge>`
- Exchanges `code` at:
  `https://<your-domain>.auth.<region>.amazoncognito.com/oauth2/token`
  with PKCE `code_verifier`.

If your app client only allows Authorization Code grant, this must use `response_type=code` (not `token`).

For local frontend with deployed Cognito:

- Add local callback/logout URLs in Cognito app client config.
- Set redirect/logout URIs to local dev URL.

For fully local backend testing:

- Leave Cognito SAM parameters empty.
- Keep `UI_JWT_STUB_TOKEN` configured.
- Paste the stub token in the UI login panel.
