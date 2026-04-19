import {
  COGNITO_CLIENT_ID,
  COGNITO_DOMAIN,
  COGNITO_LOGOUT_URI,
  COGNITO_REDIRECT_URI,
} from "../config";

function buildLoginUrl() {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    return "";
  }

  const params = new URLSearchParams({
    client_id: COGNITO_CLIENT_ID,
    response_type: "token",
    scope: "openid email profile",
    redirect_uri: COGNITO_REDIRECT_URI,
  });
  return `${COGNITO_DOMAIN}/login?${params.toString()}`;
}

function buildLogoutUrl() {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    return "";
  }
  const params = new URLSearchParams({
    client_id: COGNITO_CLIENT_ID,
    logout_uri: COGNITO_LOGOUT_URI,
  });
  return `${COGNITO_DOMAIN}/logout?${params.toString()}`;
}

export default function LoginPlaceholder({ authToken, draftToken, onTokenChange, onSaveToken, onSignOut }) {
  const loginUrl = buildLoginUrl();
  const logoutUrl = buildLogoutUrl();

  return (
    <section className="card">
      <h2>Login</h2>
      <p className="muted">Milestone 9: Cognito auth flow with local-development token fallback.</p>

      <div className="row wrap">
        <a className={`button-link ${!loginUrl ? "disabled-link" : ""}`} href={loginUrl || undefined}>
          Sign in with Cognito Hosted UI
        </a>
        <button type="button" onClick={onSignOut} disabled={!authToken}>
          Clear local token
        </button>
        <a className={`button-link ${!logoutUrl ? "disabled-link" : ""}`} href={logoutUrl || undefined}>
          Cognito logout
        </a>
      </div>

      {!loginUrl && (
        <p className="warning">
          Set <code>VITE_COGNITO_DOMAIN</code> and <code>VITE_COGNITO_CLIENT_ID</code> to enable hosted sign-in.
        </p>
      )}

      <label>
        Access token / ID token (local dev fallback)
        <textarea
          aria-label="JWT token"
          value={draftToken}
          onChange={(event) => onTokenChange(event.target.value)}
          rows={3}
          placeholder="Paste bearer token for local testing"
        />
      </label>
      <button type="button" onClick={onSaveToken}>
        Use pasted token
      </button>

      <p className="muted">Auth status: {authToken ? "Authenticated" : "Not authenticated"}</p>
    </section>
  );
}
