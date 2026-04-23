import {
  COGNITO_CLIENT_ID,
  COGNITO_DOMAIN,
  COGNITO_LOGOUT_URI,
} from "../config";

function toAbsoluteDomainUrl(domain) {
  if (!domain) {
    return "";
  }
  return domain.endsWith("/") ? domain.slice(0, -1) : domain;
}

function buildLogoutUrl() {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    return "";
  }
  const params = new URLSearchParams({
    client_id: COGNITO_CLIENT_ID,
    logout_uri: COGNITO_LOGOUT_URI,
  });
  return `${toAbsoluteDomainUrl(COGNITO_DOMAIN)}/logout?${params.toString()}`;
}

function parseJwt(token) {
  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return null;
    }
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

export default function LoginPlaceholder({
  authToken,
  draftToken,
  loginUrl,
  authHint,
  onTokenChange,
  onSaveToken,
  onSignOut,
}) {
  const logoutUrl = buildLogoutUrl();
  const jwtPayload = parseJwt(authToken);
  const expiresAt =
    jwtPayload?.exp && Number.isFinite(jwtPayload.exp)
      ? new Date(jwtPayload.exp * 1000).toISOString()
      : "";

  return (
    <section className="card">
      <h2>Login</h2>
      <p className="muted">Cognito auth flow with hosted login and local-development token fallback.</p>

      <div className="row wrap">
        <a
          className={`button-link ${!loginUrl ? "disabled-link" : ""}`}
          href={loginUrl || undefined}
        >
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
        Access token / ID token (JWT, local dev fallback)
        <textarea
          aria-label="JWT token"
          value={draftToken}
          onChange={(event) => onTokenChange(event.target.value)}
          rows={3}
          placeholder="Paste JWT bearer token (not the OAuth code)"
        />
      </label>
      <button type="button" onClick={onSaveToken}>
        Use pasted token
      </button>
      {authHint && <p className="warning">{authHint}</p>}

      <p className="muted">Auth status: {authToken ? "Authenticated" : "Not authenticated"}</p>
      {jwtPayload && (
        <p className="muted">
          JWT subject: <code>{jwtPayload.sub || jwtPayload.email || "unknown"}</code>
          {expiresAt ? ` • Expires at: ${expiresAt}` : ""}
        </p>
      )}
    </section>
  );
}
