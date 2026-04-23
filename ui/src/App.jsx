import { useEffect, useState } from "react";
import {
  API_BASE_URL,
  COGNITO_CLIENT_ID,
  COGNITO_DOMAIN,
  COGNITO_REDIRECT_URI,
} from "./config";
import CatalogDebugPanel from "./components/CatalogDebugPanel";
import LoginPlaceholder from "./components/LoginPlaceholder";
import ProfilePreferencesPanel from "./components/ProfilePreferencesPanel";
import ScheduleConfigPanel from "./components/ScheduleConfigPanel";

const TOKEN_STORAGE_KEY = "childScheduler.uiAuthToken";
const PKCE_VERIFIER_STORAGE_KEY = "childScheduler.pkceVerifier";

function trimTrailingSlash(url) {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

function tokenFromHash() {
  const hash = window.location.hash || "";
  if (!hash.startsWith("#")) {
    return "";
  }
  const params = new URLSearchParams(hash.slice(1));
  return params.get("id_token") || params.get("access_token") || "";
}

function parseCodeFromSearch() {
  const params = new URLSearchParams(window.location.search);
  return params.get("code") || "";
}

function isJwtLike(value) {
  return value.split(".").length === 3;
}

function randomBase64Url(bytes = 32) {
  const randomBytes = crypto.getRandomValues(new Uint8Array(bytes));
  return btoa(String.fromCharCode(...randomBytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

async function sha256Base64Url(input) {
  const encoded = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

async function exchangeCodeForTokens(code) {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    return "";
  }
  const verifier = localStorage.getItem(PKCE_VERIFIER_STORAGE_KEY) || "";
  if (!verifier) {
    return "";
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: COGNITO_CLIENT_ID,
    redirect_uri: COGNITO_REDIRECT_URI,
    code,
    code_verifier: verifier,
  });
  const tokenEndpoint = `${trimTrailingSlash(COGNITO_DOMAIN)}/oauth2/token`;
  const response = await fetch(tokenEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    return "";
  }
  const payload = await response.json();
  return payload.id_token || payload.access_token || "";
}

async function buildHostedLoginUrl() {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    return "";
  }
  const verifier = randomBase64Url(64);
  const challenge = await sha256Base64Url(verifier);
  localStorage.setItem(PKCE_VERIFIER_STORAGE_KEY, verifier);
  const params = new URLSearchParams({
    response_type: "code",
    client_id: COGNITO_CLIENT_ID,
    redirect_uri: COGNITO_REDIRECT_URI,
    scope: "openid email profile",
    code_challenge_method: "S256",
    code_challenge: challenge,
  });
  return `${trimTrailingSlash(COGNITO_DOMAIN)}/oauth2/authorize?${params.toString()}`;
}

export default function App() {
  const [authToken, setAuthToken] = useState(localStorage.getItem(TOKEN_STORAGE_KEY) || "");
  const [draftToken, setDraftToken] = useState("");
  const [loginUrl, setLoginUrl] = useState("");
  const [authHint, setAuthHint] = useState("");

  useEffect(() => {
    let mounted = true;

    async function initializeAuth() {
      if (COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
        const generatedLoginUrl = await buildHostedLoginUrl();
        if (mounted) {
          setLoginUrl(generatedLoginUrl);
        }
      }

      const code = parseCodeFromSearch();
      if (code) {
        const codeToken = await exchangeCodeForTokens(code);
        if (codeToken && mounted) {
          localStorage.setItem(TOKEN_STORAGE_KEY, codeToken);
          localStorage.removeItem(PKCE_VERIFIER_STORAGE_KEY);
          setAuthToken(codeToken);
          setDraftToken("");
          const nextUrl = `${window.location.pathname}`;
          window.history.replaceState({}, document.title, nextUrl);
          return;
        }
        if (mounted) {
          setAuthHint(
            "Found OAuth code in URL but token exchange failed. Please sign in again from this browser tab, or paste a JWT access/id token (not the code value).",
          );
        }
      }

      const hashToken = tokenFromHash();
      if (!hashToken || !mounted) {
        return;
      }

      localStorage.setItem(TOKEN_STORAGE_KEY, hashToken);
      setAuthToken(hashToken);
      setDraftToken("");

      const nextUrl = `${window.location.pathname}${window.location.search}`;
      window.history.replaceState({}, document.title, nextUrl);
    }

    initializeAuth();
    return () => {
      mounted = false;
    };
  }, []);

  function saveDraftToken() {
    const candidate = draftToken.trim();
    if (!candidate) {
      return;
    }
    setAuthHint("");
    if (isJwtLike(candidate)) {
      localStorage.setItem(TOKEN_STORAGE_KEY, candidate);
      setAuthToken(candidate);
      setDraftToken("");
      return;
    }

    if (COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
      exchangeCodeForTokens(candidate)
        .then((token) => {
          if (token) {
            localStorage.setItem(TOKEN_STORAGE_KEY, token);
            setAuthToken(token);
            setDraftToken("");
            return;
          }
          setAuthHint(
            "The pasted value is not a JWT and could not be exchanged as an OAuth code. Paste the JWT access/id token from Cognito login response.",
          );
        })
        .catch(() => {
          setAuthHint(
            "Token exchange failed for pasted value. Paste a JWT access/id token, or complete hosted sign-in in this same browser tab.",
          );
        });
      return;
    }

    setAuthHint(
      "The pasted value does not look like a JWT bearer token. Paste an access/id token (three dot-separated segments), not the authorization code.",
    );
  }

  function signOut() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setAuthToken("");
    setDraftToken("");
  }

  return (
    <main className="app-shell">
      <header>
        <h1>Child Scheduler</h1>
        <p className="muted">Milestone 9: Cognito integration enabled</p>
        <p className="muted">API Base URL: {API_BASE_URL}</p>
      </header>

      <LoginPlaceholder
        authToken={authToken}
        draftToken={draftToken}
        loginUrl={loginUrl}
        onTokenChange={setDraftToken}
        onSaveToken={saveDraftToken}
        onSignOut={signOut}
        authHint={authHint}
      />
      <CatalogDebugPanel authToken={authToken} />
      <ScheduleConfigPanel authToken={authToken} />
      <ProfilePreferencesPanel authToken={authToken} />
    </main>
  );
}
